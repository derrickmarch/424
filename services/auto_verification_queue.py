"""
Automatic verification queue - processes verifications sequentially with immediate hangup on success.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import asyncio
import structlog
from models import AccountVerification, VerificationStatus
from services.call_orchestrator import CallOrchestrator
from services.verification_service import VerificationService

logger = structlog.get_logger()


class AutoVerificationQueue:
    """
    Automatically processes pending verifications one by one.
    Hangs up immediately when account is verified, then moves to next.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.orchestrator = CallOrchestrator(db)
        self.verification_service = VerificationService(db)
        self.is_running = False
        self.current_call_sid: Optional[str] = None
        self.current_verification_id: Optional[str] = None
    
    async def process_queue(self, max_verifications: Optional[int] = None):
        """
        Process verification queue automatically.
        
        Args:
            max_verifications: Maximum number to process (None = all pending)
        """
        if self.is_running:
            logger.warning("Queue processor already running")
            return
        
        self.is_running = True
        processed = 0
        successful = 0
        failed = 0
        
        try:
            logger.info("🚀 Starting automatic verification queue")
            
            while True:
                # Get next pending verification
                pending = self.verification_service.get_pending_verifications(limit=1)
                
                if not pending:
                    logger.info("✅ No more pending verifications")
                    break
                
                if max_verifications and processed >= max_verifications:
                    logger.info(f"✅ Reached max verifications limit: {max_verifications}")
                    break
                
                verification = pending[0]
                self.current_verification_id = verification.verification_id
                
                try:
                    logger.info(f"📞 Processing verification {verification.verification_id}")
                    
                    # Check if should retry
                    should_retry, wait_minutes = self.orchestrator.should_retry(verification.verification_id)
                    if not should_retry:
                        logger.info(f"⏭️ Skipping {verification.verification_id} - retry wait needed")
                        continue
                    
                    # Initiate call
                    from config import settings
                    call_sid = self.orchestrator.initiate_call(
                        verification.verification_id,
                        settings.twilio_webhook_base_url
                    )
                    
                    self.current_call_sid = call_sid
                    logger.info(f"📞 Call initiated: {call_sid}")
                    
                    # Wait for call to complete (in mock mode this is fast)
                    # In production, this would be handled via webhooks
                    await asyncio.sleep(5)
                    
                    # Check result
                    self.db.refresh(verification)
                    
                    if verification.account_exists:
                        logger.info(f"✅ Account verified for {verification.verification_id} - Moving to next")
                        successful += 1
                    elif verification.status == VerificationStatus.FAILED:
                        logger.warning(f"❌ Verification failed for {verification.verification_id}")
                        failed += 1
                    else:
                        logger.info(f"⏳ Verification in progress: {verification.verification_id}")
                    
                    processed += 1
                    
                    # Small delay before next call
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {verification.verification_id}: {e}")
                    failed += 1
                    continue
                
                finally:
                    self.current_call_sid = None
                    self.current_verification_id = None
        
        finally:
            self.is_running = False
            logger.info(f"📊 Queue processing complete: {processed} processed, {successful} successful, {failed} failed")
        
        return {
            'processed': processed,
            'successful': successful,
            'failed': failed
        }
    
    def stop_processing(self):
        """Stop the queue processor."""
        if self.is_running:
            self.is_running = False
            logger.info("🛑 Stopping queue processor")
            
            # Optionally hang up current call
            if self.current_call_sid:
                from services.telephony import get_telephony_service
                telephony = get_telephony_service(self.db)
                try:
                    telephony.hangup_call(self.current_call_sid)
                    logger.info(f"📞 Hung up current call: {self.current_call_sid}")
                except Exception as e:
                    logger.error(f"Failed to hang up call: {e}")


# Add instant hangup after verification confirmed
def handle_verification_confirmed(db: Session, call_sid: str, verification_id: str):
    """
    Called when account is verified - immediately hangs up and processes next.
    
    Args:
        db: Database session
        call_sid: Current call SID
        verification_id: Verification that was just confirmed
    """
    from services.telephony import get_telephony_service
    from api.call_monitor import call_monitor
    
    logger.info(f"✅ Account verified for {verification_id} - hanging up immediately")
    
    # Add event to monitor
    call_monitor.add_event(call_sid, "verification_confirmed", "Account verified - ending call immediately")
    call_monitor.update_status(call_sid, "verified_hangup")
    
    # Hang up the call
    telephony = get_telephony_service(db)
    try:
        telephony.hangup_call(call_sid)
        logger.info(f"📞 Call {call_sid} hung up successfully")
        call_monitor.add_event(call_sid, "call_ended", "Call terminated after verification")
    except Exception as e:
        logger.error(f"Failed to hang up call {call_sid}: {e}")
    
    # Mark call as completed
    call_monitor.end_call(call_sid, "completed_verified")
    
    logger.info(f"✅ Verification {verification_id} complete - ready for next")
