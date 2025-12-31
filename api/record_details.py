"""
API endpoint for detailed record viewing with logs.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from api.auth import get_current_user
from models import User, AccountVerification, CallLog
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/record-details", tags=["record-details"])


@router.get("/{verification_id}")
async def get_record_details(
    verification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get complete details for a verification record including all logs."""
    try:
        # Get verification
        verification = db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        # Get all call logs for this verification
        call_logs = db.query(CallLog).filter(
            CallLog.verification_id == verification_id
        ).order_by(CallLog.created_at.desc()).all()
        
        # Build response
        return {
            "verification": {
                "verification_id": verification.verification_id,
                "customer_name": verification.customer_name,
                "customer_phone": verification.customer_phone,
                "customer_email": verification.customer_email,
                "customer_address": verification.customer_address,
                "account_number": verification.account_number,
                "customer_date_of_birth": verification.customer_date_of_birth,
                "customer_ssn_last4": verification.customer_ssn_last4,
                "company_name": verification.company_name,
                "company_phone": verification.company_phone,
                "status": verification.status.value,
                "attempt_count": verification.attempt_count,
                "last_attempt_at": verification.last_attempt_at.isoformat() if verification.last_attempt_at else None,
                "call_sid": verification.call_sid,
                "call_duration_seconds": verification.call_duration_seconds,
                "result_json": verification.result_json,
                "call_summary": verification.call_summary,
                "transcript": verification.transcript,
                "call_outcome": verification.call_outcome.value if verification.call_outcome else None,
                "account_exists": verification.account_exists,
                "account_details": verification.account_details,
                "created_at": verification.created_at.isoformat(),
                "updated_at": verification.updated_at.isoformat(),
                "completed_at": verification.completed_at.isoformat() if verification.completed_at else None,
                "follow_up_needed": verification.follow_up_needed,
                "recording_consent_given": verification.recording_consent_given,
                "priority": verification.priority,
                "verification_instruction": verification.verification_instruction,
                "information_to_collect": verification.information_to_collect,
                "additional_customer_info": verification.additional_customer_info
            },
            "call_logs": [
                {
                    "id": log.id,
                    "call_sid": log.call_sid,
                    "direction": log.direction,
                    "from_number": log.from_number,
                    "to_number": log.to_number,
                    "call_status": log.call_status,
                    "call_outcome": log.call_outcome.value if log.call_outcome else None,
                    "initiated_at": log.initiated_at.isoformat() if log.initiated_at else None,
                    "answered_at": log.answered_at.isoformat() if log.answered_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_seconds": log.duration_seconds,
                    "conversation_log": log.conversation_log,
                    "error_message": log.error_message,
                    "attempt_number": log.attempt_number,
                    "created_at": log.created_at.isoformat()
                }
                for log in call_logs
            ],
            "summary": {
                "total_attempts": verification.attempt_count,
                "total_call_duration": verification.call_duration_seconds or 0,
                "has_transcript": bool(verification.transcript),
                "has_recording": bool(verification.recording_consent_given),
                "needs_follow_up": verification.follow_up_needed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting record details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
