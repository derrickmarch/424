"""
Business logic for account verification management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from models import AccountVerification, VerificationStatus, CallOutcome, Blocklist
from schemas import AccountVerificationCreate, CallResultSchema, SystemStats
import logging

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for managing account verifications."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_verification(self, verification_data: AccountVerificationCreate) -> AccountVerification:
        """Create a new account verification request."""
        # Check if phone is in blocklist
        if self.is_blocked(verification_data.company_phone):
            logger.warning(f"Phone {verification_data.company_phone} is in blocklist")
            raise ValueError(f"Phone number {verification_data.company_phone} is blocked")
        
        # Check if verification already exists
        existing = self.db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_data.verification_id
        ).first()
        
        if existing:
            raise ValueError(f"Verification {verification_data.verification_id} already exists")
        
        verification = AccountVerification(
            verification_id=verification_data.verification_id,
            customer_name=verification_data.customer_name,
            customer_phone=verification_data.customer_phone,
            company_name=verification_data.company_name,
            company_phone=verification_data.company_phone,
            customer_email=verification_data.customer_email,
            customer_address=verification_data.customer_address,
            account_number=verification_data.account_number,
            customer_date_of_birth=verification_data.customer_date_of_birth,
            customer_ssn_last4=verification_data.customer_ssn_last4,
            additional_customer_info=verification_data.additional_customer_info,
            verification_instruction=verification_data.verification_instruction,
            information_to_collect=verification_data.information_to_collect,
            priority=verification_data.priority,
            status=VerificationStatus.PENDING,
            attempt_count=0,
        )
        
        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)
        
        logger.info(f"Created verification {verification.verification_id}")
        return verification
    
    def get_verification(self, verification_id: str) -> Optional[AccountVerification]:
        """Get a verification by ID."""
        return self.db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
    
    def get_pending_verifications(self, limit: Optional[int] = None) -> List[AccountVerification]:
        """Get all pending verifications."""
        query = self.db.query(AccountVerification).filter(
            AccountVerification.status == VerificationStatus.PENDING
        ).order_by(
            AccountVerification.priority.desc(),
            AccountVerification.created_at.asc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_as_calling(self, verification_id: str, call_sid: str) -> AccountVerification:
        """Mark verification as currently being called."""
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        verification.status = VerificationStatus.CALLING
        verification.attempt_count += 1
        verification.last_attempt_at = datetime.utcnow()
        verification.call_sid = call_sid
        
        self.db.commit()
        self.db.refresh(verification)
        
        logger.info(f"Marked verification {verification_id} as calling (attempt #{verification.attempt_count})")
        return verification
    
    def update_call_result(
        self,
        verification_id: str,
        result: CallResultSchema,
        call_summary: str,
        transcript: Optional[str] = None,
        call_duration: Optional[int] = None
    ) -> AccountVerification:
        """Update verification with call results."""
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        # Determine final status
        if result.call_outcome == CallOutcome.ACCOUNT_FOUND:
            verification.status = VerificationStatus.VERIFIED
            verification.account_exists = True
            verification.completed_at = datetime.utcnow()
        elif result.call_outcome == CallOutcome.ACCOUNT_NOT_FOUND:
            verification.status = VerificationStatus.NOT_FOUND
            verification.account_exists = False
            verification.completed_at = datetime.utcnow()
        elif result.call_outcome == CallOutcome.NEEDS_HUMAN:
            verification.status = VerificationStatus.NEEDS_HUMAN
        elif result.call_outcome in [CallOutcome.VOICEMAIL, CallOutcome.NO_ANSWER, CallOutcome.BUSY]:
            # Keep as pending for retry if attempts remain
            from config import settings
            if verification.attempt_count >= settings.max_retry_attempts:
                verification.status = VerificationStatus.FAILED
            else:
                verification.status = VerificationStatus.PENDING
        else:
            verification.status = VerificationStatus.FAILED
        
        # Store results
        verification.result_json = result.model_dump()
        verification.call_summary = call_summary
        verification.call_outcome = result.call_outcome
        verification.follow_up_needed = result.follow_up_needed
        verification.account_details = result.account_details
        
        if transcript:
            verification.transcript = transcript
        
        if call_duration:
            verification.call_duration_seconds = call_duration
        
        self.db.commit()
        self.db.refresh(verification)
        
        logger.info(f"Updated verification {verification_id} with outcome: {result.call_outcome}")
        return verification
    
    def mark_as_failed(self, verification_id: str, error_message: str) -> AccountVerification:
        """Mark verification as failed."""
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        verification.status = VerificationStatus.FAILED
        verification.call_summary = f"Failed: {error_message}"
        
        self.db.commit()
        self.db.refresh(verification)
        
        logger.error(f"Marked verification {verification_id} as failed: {error_message}")
        return verification
    
    def is_blocked(self, phone_number: str) -> bool:
        """Check if a phone number is in the blocklist."""
        return self.db.query(Blocklist).filter(
            Blocklist.phone_number == phone_number
        ).first() is not None
    
    def add_to_blocklist(self, phone_number: str, reason: str, added_by: str = "system") -> Blocklist:
        """Add a phone number to the blocklist."""
        existing = self.db.query(Blocklist).filter(
            Blocklist.phone_number == phone_number
        ).first()
        
        if existing:
            logger.warning(f"Phone {phone_number} already in blocklist")
            return existing
        
        blocklist_entry = Blocklist(
            phone_number=phone_number,
            reason=reason,
            added_by=added_by
        )
        
        self.db.add(blocklist_entry)
        self.db.commit()
        self.db.refresh(blocklist_entry)
        
        logger.info(f"Added {phone_number} to blocklist: {reason}")
        return blocklist_entry
    
    def get_system_stats(self) -> SystemStats:
        """Get system statistics."""
        total = self.db.query(func.count(AccountVerification.verification_id)).scalar()
        
        status_counts = {}
        for status in VerificationStatus:
            count = self.db.query(func.count(AccountVerification.verification_id)).filter(
                AccountVerification.status == status
            ).scalar()
            status_counts[status.value] = count
        
        # Calculate success rate
        verified = status_counts.get(VerificationStatus.VERIFIED.value, 0)
        not_found = status_counts.get(VerificationStatus.NOT_FOUND.value, 0)
        completed = verified + not_found
        success_rate = (verified / completed * 100) if completed > 0 else 0.0
        
        # Calculate average duration
        avg_duration = self.db.query(func.avg(AccountVerification.call_duration_seconds)).filter(
            AccountVerification.call_duration_seconds.isnot(None)
        ).scalar()
        
        return SystemStats(
            total_verifications=total,
            pending=status_counts.get(VerificationStatus.PENDING.value, 0),
            calling=status_counts.get(VerificationStatus.CALLING.value, 0),
            verified=verified,
            not_found=not_found,
            needs_human=status_counts.get(VerificationStatus.NEEDS_HUMAN.value, 0),
            failed=status_counts.get(VerificationStatus.FAILED.value, 0),
            success_rate=round(success_rate, 2),
            average_duration_seconds=round(float(avg_duration), 2) if avg_duration else None
        )
