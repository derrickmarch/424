"""
Call orchestrator - manages the end-to-end calling workflow with looping support.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from models import CallLog, CallOutcome, CallSchedule
from schemas import CallContext
from services.verification_service import VerificationService
from services.telephony import get_telephony_service
from services.ai_agent_service import ai_agent_service
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Import call monitor for real-time tracking
def get_call_monitor():
    """Lazy import to avoid circular dependency."""
    from api.call_monitor import call_monitor
    return call_monitor


class CallOrchestrator:
    """Orchestrates the end-to-end calling process for account verifications."""
    
    def __init__(self, db: Session):
        self.db = db
        self.telephony = get_telephony_service(db)
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
        
        # Check provider account balance before making call
        try:
            balance_info = self.telephony.get_account_balance()
            if 'error' not in balance_info:
                balance = float(balance_info.get('balance', 0))
                currency = balance_info.get('currency', 'USD')
                
                # Warn if balance is low (less than $5)
                if balance < 5.0:
                    logger.warning(f"⚠️ LOW BALANCE WARNING: Provider balance is {currency} {balance:.2f}")
                    if balance <= 0 and not settings.get_test_mode():
                        raise ValueError(f"Insufficient balance ({currency} {balance:.2f}). Please add funds to your account.")
                else:
                    logger.info(f"✓ Provider balance check: {currency} {balance:.2f}")
        except ValueError:
            # Re-raise insufficient balance errors
            raise
        except Exception as e:
            # Log balance check errors but don't block calls (might be trial account limitations)
            logger.warning(f"Could not check provider balance (continuing anyway): {e}")
        
        # Check if we should retry
        should_retry, wait_minutes = self.should_retry(verification_id)
        if not should_retry:
            if wait_minutes:
                raise ValueError(f"Must wait {wait_minutes} more minutes before retry")
            else:
                raise ValueError(f"Verification {verification_id} has exceeded max retry attempts")
        
        # Build webhook URLs based on selected provider
        from services.settings_service import get_runtime_settings
        runtime = get_runtime_settings(self.db)
        provider = (runtime.get("telephony_provider", "twilio") or "twilio").lower()

        # Choose base URL precedence: provider-specific (DB) > provided arg > env setting
        provided_base = (webhook_base_url or "").rstrip("/") if webhook_base_url else ""
        if provider == "vonage":
            vonage_base = (runtime.get("vonage_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url).rstrip("/")
            voice_webhook_url = f"{vonage_base}/api/vonage/answer?verification_id={verification_id}"
            status_callback_url = f"{vonage_base}/api/vonage/event"
        elif provider == "bland":
            bland_base = (runtime.get("bland_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url or "").rstrip("/")
            # Validation handled similarly as before
            try:
                from urllib.parse import urlparse
                host = urlparse(bland_base).hostname or ""
                is_test = settings.get_test_mode()
                if not is_test:
                    if not bland_base:
                        raise RuntimeError("Bland webhook base URL is required in live mode.")
                    if "ngrok" in host or host in ("localhost", "127.0.0.1"):
                        raise RuntimeError("In live mode, configure a public custom domain for webhooks (not ngrok/localhost).")
            except Exception:
                raise
            voice_webhook_url = f"{bland_base}/api/bland/webhook" if bland_base else ""
            status_callback_url = f"{bland_base}/api/bland/webhook" if bland_base else ""
        elif provider == "telnyx":
            telnyx_base = (runtime.get("telnyx_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url or "").rstrip("/")
            voice_webhook_url = f"{telnyx_base}/api/telnyx/webhook" if telnyx_base else ""
            status_callback_url = f"{telnyx_base}/api/telnyx/webhook" if telnyx_base else ""
        elif provider == "plivo":
            plivo_base = (runtime.get("plivo_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url or "").rstrip("/")
            voice_webhook_url = f"{plivo_base}/api/plivo/webhook" if plivo_base else ""
            status_callback_url = f"{plivo_base}/api/plivo/webhook" if plivo_base else ""
        elif provider == "signalwire":
            sw_base = (runtime.get("signalwire_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url or "").rstrip("/")
            voice_webhook_url = f"{sw_base}/api/signalwire/webhook" if sw_base else ""
            status_callback_url = f"{sw_base}/api/signalwire/webhook" if sw_base else ""
            bland_base = (runtime.get("bland_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url or "").rstrip("/")
            # In TEST mode we allow ngrok/localhost; in LIVE mode we require a custom public domain
            try:
                from urllib.parse import urlparse
                host = urlparse(bland_base).hostname or ""
                is_test = settings.get_test_mode()
                if not is_test:
                    if not bland_base:
                        raise RuntimeError("Bland webhook base URL is required in live mode.")
                    if "ngrok" in host or host in ("localhost", "127.0.0.1"):
                        raise RuntimeError("In live mode, configure a public custom domain for webhooks (not ngrok/localhost).")
                else:
                    if not bland_base:
                        logger.warning("TEST MODE: bland_webhook_base_url is empty. Set it to your ngrok URL to receive webhooks during tests.")
            except Exception as _e:
                # If validation fails, re-raise so the caller can surface to user
                raise
            # Bland agent will call this webhook with results
            voice_webhook_url = f"{bland_base}/api/bland/webhook" if bland_base else ""
            status_callback_url = f"{bland_base}/api/bland/webhook" if bland_base else ""
        else:
            twilio_base = (runtime.get("twilio_webhook_base_url", None) or provided_base or settings.twilio_webhook_base_url).rstrip("/")
            voice_webhook_url = f"{twilio_base}/api/twilio/voice?verification_id={verification_id}"
            status_callback_url = f"{twilio_base}/api/twilio/status-callback"
        
        try:
            # Start call monitoring
            monitor = get_call_monitor()
            
            # Initiate the call via Twilio
            logger.info(f"🔄 Initiating call for verification {verification_id}")
            monitor.add_event(verification_id, "preparation", "Preparing to make call", {
                "to_number": verification.company_phone,
                "company": verification.company_name
            })
            
            call_sid = self.telephony.make_outbound_call(
                to_number=verification.company_phone,
                verification_id=verification_id,
                webhook_url=voice_webhook_url,
                status_callback_url=status_callback_url
            )
            
            # Register call with monitor
            monitor.start_call(call_sid, verification_id, verification.company_phone)
            monitor.add_event(call_sid, "call_initiated", f"Call initiated to {verification.company_phone}", {
                "call_sid": call_sid,
                "verification_id": verification_id
            })
            
            # Update verification status
            self.verification_service.mark_as_calling(verification_id, call_sid)
            
            # Create call log entry
            call_log = CallLog(
                verification_id=verification_id,
                call_sid=call_sid,
                direction="outbound",
                from_number=self.telephony.get_from_number() or settings.twilio_phone_number,
                to_number=verification.company_phone,
                call_status="initiated",
                attempt_number=verification.attempt_count,
                initiated_at=datetime.utcnow()
            )
            self.db.add(call_log)
            self.db.commit()
            
            monitor.add_event(call_sid, "database_updated", "Call log created in database")
            logger.info(f"✅ Initiated call {call_sid} for verification {verification_id}")
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
            # Get monitor
            monitor = get_call_monitor()
            monitor.add_event(call_sid, "processing_started", "Processing call results")
            
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
            
            monitor.add_event(call_sid, "ai_processing", "AI analyzing conversation")
            
            # Process the conversation with AI
            result, summary = ai_agent_service.process_conversation(
                call_context,
                conversation_transcript
            )
            
            monitor.add_event(call_sid, "ai_result", f"AI decision: {result.call_outcome}", {
                "outcome": result.call_outcome.value,
                "account_exists": result.account_exists,
                "summary": summary
            })
            
            # If account is verified, hang up immediately and move to next
            if result.account_exists and result.call_outcome == CallOutcome.ACCOUNT_FOUND:
                logger.info(f"✅ Account verified for {verification.verification_id} - ending call immediately")
                monitor.add_event(call_sid, "auto_hangup", "Account verified - terminating call to save time")
                
                from services.auto_verification_queue import handle_verification_confirmed
                handle_verification_confirmed(self.db, call_sid, verification.verification_id)
            
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
            logger.error(f"Error handling completed call {call_sid}: {e}", exc_info=True)
            self.verification_service.mark_as_failed(verification.verification_id, str(e))
    
    async def process_batch(self, max_verifications: Optional[int] = None):
        """
        Process a batch of pending verifications sequentially.
        
        Args:
            max_verifications: Maximum number of verifications to process
        """
        # Check provider balance before processing batch
        try:
            balance_info = self.telephony.get_account_balance()
            if 'error' not in balance_info:
                balance = float(balance_info.get('balance', 0))
                currency = balance_info.get('currency', 'USD')
                logger.info(f"📊 Starting batch with provider balance: {currency} {balance:.2f}")
                
                if balance < 2.0 and not settings.get_test_mode():
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
