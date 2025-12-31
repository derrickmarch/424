"""
Call orchestrator - manages the end-to-end calling workflow with looping support.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from models import CallLog, CallOutcome, CallSchedule
from schemas import CallContext
from services.verification_service import VerificationService
from services.twilio_service import get_twilio_service
from services.ai_agent_service import ai_agent_service
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class CallOrchestrator:
    """Orchestrates the end-to-end calling process for account verifications."""
    
    def __init__(self, db: Session):
        self.db = db
        self.twilio_service = get_twilio_service(db)
        self.verification_service = VerificationService(db)
    
    def should_retry(self, verification_id: str) -> tuple[bool, Optional[int]]:
        """
        Determine if a verification should be retried.
        
        Returns:
            Tuple of (should_retry, wait_minutes)
        """
        verification = self.verification_service.get_verification(verification_id)
        if not verification:
            return False, None
        
        # Check attempt count
        if verification.attempt_count >= settings.max_retry_attempts:
            logger.info(f"Verification {verification_id} exceeded max retry attempts")
            return False, None
        
        # Check if enough time has passed since last attempt
        if verification.last_attempt_at:
            backoff_list = settings.retry_backoff_list
            attempt_index = min(verification.attempt_count - 1, len(backoff_list) - 1)
            wait_minutes = backoff_list[attempt_index]
            
            next_attempt_time = verification.last_attempt_at + timedelta(minutes=wait_minutes)
            if datetime.utcnow() < next_attempt_time:
                remaining_minutes = int((next_attempt_time - datetime.utcnow()).total_seconds() / 60)
                logger.info(f"Verification {verification_id} needs to wait {remaining_minutes} more minutes")
                return False, remaining_minutes
        
        return True, 0
    
    def initiate_call(self, verification_id: str, webhook_base_url: str) -> str:
        """
        Initiate an outbound call for a verification.
        
        Args:
            verification_id: The verification to call
            webhook_base_url: Base URL for webhooks
        
        Returns:
            call_sid: Twilio Call SID
        """
        verification = self.verification_service.get_verification(verification_id)
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        # Check Twilio account balance before making call
        try:
            balance_info = twilio_service.get_account_balance()
            if 'error' not in balance_info:
                balance = float(balance_info.get('balance', 0))
                currency = balance_info.get('currency', 'USD')
                
                # Warn if balance is low (less than $5)
                if balance < 5.0:
                    logger.warning(f"⚠️ LOW BALANCE WARNING: Twilio account balance is {currency} {balance:.2f}")
                    if balance <= 0:
                        raise ValueError(f"Insufficient Twilio balance ({currency} {balance:.2f}). Please add funds to your account.")
                else:
                    logger.info(f"✓ Twilio balance check: {currency} {balance:.2f}")
        except ValueError:
            # Re-raise insufficient balance errors
            raise
        except Exception as e:
            # Log balance check errors but don't block calls (might be trial account limitations)
            logger.warning(f"Could not check Twilio balance (continuing anyway): {e}")
        
        # Check if we should retry
        should_retry, wait_minutes = self.should_retry(verification_id)
        if not should_retry:
            if wait_minutes:
                raise ValueError(f"Must wait {wait_minutes} more minutes before retry")
            else:
                raise ValueError(f"Verification {verification_id} has exceeded max retry attempts")
        
        # Build webhook URLs
        voice_webhook_url = f"{webhook_base_url}/api/twilio/voice?verification_id={verification_id}"
        status_callback_url = f"{webhook_base_url}/api/twilio/status-callback"
        
        try:
            # Initiate the call via Twilio
            call_sid = self.twilio_service.make_outbound_call(
                to_number=verification.company_phone,
                verification_id=verification_id,
                webhook_url=voice_webhook_url,
                status_callback_url=status_callback_url
            )
            
            # Update verification status
            self.verification_service.mark_as_calling(verification_id, call_sid)
            
            # Create call log entry
            call_log = CallLog(
                verification_id=verification_id,
                call_sid=call_sid,
                direction="outbound",
                from_number=settings.twilio_phone_number,
                to_number=verification.company_phone,
                call_status="initiated",
                attempt_number=verification.attempt_count,
                initiated_at=datetime.utcnow()
            )
            self.db.add(call_log)
            self.db.commit()
            
            logger.info(f"Initiated call {call_sid} for verification {verification_id}")
            return call_sid
            
        except Exception as e:
            logger.error(f"Failed to initiate call for verification {verification_id}: {e}")
            self.verification_service.mark_as_failed(verification_id, str(e))
            raise
    
    def handle_call_completed(
        self,
        call_sid: str,
        conversation_transcript: str,
        call_duration: int,
        recording_consent_given: bool = False
    ):
        """
        Handle a completed call - process results and update database.
        
        Args:
            call_sid: Twilio Call SID
            conversation_transcript: Full transcript of the call
            call_duration: Duration in seconds
            recording_consent_given: Whether user consented to recording
        """
        from models import AccountVerification
        
        # Find the verification by call_sid
        verification = self.db.query(AccountVerification).filter(
            AccountVerification.call_sid == call_sid
        ).first()
        
        if not verification:
            logger.error(f"No verification found for call_sid {call_sid}")
            return
        
        try:
            # Create call context
            call_context = CallContext(
                verification_id=verification.verification_id,
                customer_name=verification.customer_name,
                customer_phone=verification.customer_phone,
                company_name=verification.company_name,
                company_phone=verification.company_phone,
                customer_email=verification.customer_email,
                account_number=verification.account_number,
                verification_instruction=verification.verification_instruction,
                attempt_number=verification.attempt_count
            )
            
            # Process the conversation with AI
            result, summary = ai_agent_service.process_conversation(
                call_context,
                conversation_transcript
            )
            
            # Determine if we should store transcript
            transcript_to_store = None
            if settings.enable_transcription and recording_consent_given:
                transcript_to_store = conversation_transcript
            
            # Update verification with results
            self.verification_service.update_call_result(
                verification_id=verification.verification_id,
                result=result,
                call_summary=summary,
                transcript=transcript_to_store,
                call_duration=call_duration
            )
            
            # Update call log
            call_log = self.db.query(CallLog).filter(
                CallLog.call_sid == call_sid
            ).order_by(CallLog.created_at.desc()).first()
            
            if call_log:
                call_log.completed_at = datetime.utcnow()
                call_log.duration_seconds = call_duration
                call_log.call_outcome = result.call_outcome
                call_log.call_status = "completed"
                self.db.commit()
            
            logger.info(f"Completed call {call_sid} for verification {verification.verification_id}: {result.call_outcome}")
            
        except Exception as e:
            logger.error(f"Error handling completed call {call_sid}: {e}")
            self.verification_service.mark_as_failed(verification.verification_id, str(e))
    
    async def process_batch(self, max_verifications: Optional[int] = None):
        """
        Process a batch of pending verifications sequentially.
        
        Args:
            max_verifications: Maximum number of verifications to process
        """
        # Check Twilio balance before processing batch
        try:
            balance_info = twilio_service.get_account_balance()
            if 'error' not in balance_info:
                balance = float(balance_info.get('balance', 0))
                currency = balance_info.get('currency', 'USD')
                logger.info(f"📊 Starting batch with Twilio balance: {currency} {balance:.2f}")
                
                if balance < 2.0:
                    logger.error(f"⚠️ Batch processing cancelled: Insufficient balance ({currency} {balance:.2f})")
                    return 0, 0, 0
                elif balance < 5.0:
                    logger.warning(f"⚠️ LOW BALANCE: {currency} {balance:.2f} - Consider adding funds soon")
        except Exception as e:
            logger.warning(f"Could not check balance before batch (continuing anyway): {e}")
        
        pending_verifications = self.verification_service.get_pending_verifications(
            limit=max_verifications
        )
        
        logger.info(f"Starting batch processing of {len(pending_verifications)} verifications")
        
        processed = 0
        successful = 0
        failed = 0
        
        for verification in pending_verifications:
            try:
                # Check if we should retry this verification
                should_retry, wait_minutes = self.should_retry(verification.verification_id)
                if not should_retry:
                    continue
                
                # Initiate the call
                webhook_base_url = settings.twilio_webhook_base_url
                call_sid = self.initiate_call(verification.verification_id, webhook_base_url)
                
                logger.info(f"Initiated call {call_sid} for verification {verification.verification_id}")
                processed += 1
                successful += 1
                
                # Wait for call to complete (in production, this would be async via webhooks)
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error processing verification {verification.verification_id}: {e}")
                failed += 1
                continue
        
        logger.info(f"Batch processing completed: {processed} processed, {successful} successful, {failed} failed")
        return processed, successful, failed
    
    def update_schedule(self, processed: int, successful: int, failed: int):
        """Update the call schedule tracking."""
        schedule = self.db.query(CallSchedule).order_by(
            CallSchedule.created_at.desc()
        ).first()
        
        if not schedule:
            schedule = CallSchedule()
            self.db.add(schedule)
        
        schedule.last_run_at = datetime.utcnow()
        schedule.next_run_at = datetime.utcnow() + timedelta(minutes=settings.call_loop_interval_minutes)
        schedule.verifications_processed += processed
        schedule.verifications_successful += successful
        schedule.verifications_failed += failed
        schedule.is_running = False
        
        self.db.commit()
        logger.info(f"Updated schedule: next run at {schedule.next_run_at}")


from models import AccountVerification
