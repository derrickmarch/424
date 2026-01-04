"""
API routes for Vonage (Nexmo) webhooks.
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.verification_service import VerificationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vonage", tags=["vonage"]) 


@router.post("/answer")
async def vonage_answer(
    request: Request,
    verification_id: str,
    db: Session = Depends(get_db)
):
    """
    Vonage answer webhook (answer_url). Return NCCO instructing what to do when the call is answered.
    """
    try:
        service = VerificationService(db)
        verification = service.get_verification(verification_id)
        if not verification:
            # Simple message then hangup
            ncco = [
                {"action": "talk", "text": "We could not find the verification. Goodbye."}
            ]
            return ncco

        message = (
            f"Hi! This is an automated assistant calling to verify account information. "
            f"We are checking if you have an account on file for {verification.customer_name}. "
            f"The phone number we have is {verification.customer_phone}. "
            f"Can you confirm if this account exists in your system?"
        )
        ncco = [
            {"action": "talk", "text": message},
            {"action": "talk", "text": "Thank you for your time. Goodbye."}
        ]
        return ncco
    except Exception as e:
        logger.error(f"Vonage answer error: {e}")
        return [{"action": "talk", "text": "An error occurred. Goodbye."}]


@router.post("/event")
async def vonage_event(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Vonage event webhook (event_url). Receives call status updates.
    """
    try:
        data = await request.json()
        status = data.get("status")
        uuid = data.get("uuid") or data.get("conversation_uuid")
        logger.info(f"Vonage status: {uuid} - {status}")

        # Update call log if we have it
        from models import CallLog
        call_log = db.query(CallLog).filter(CallLog.call_sid == uuid).order_by(CallLog.created_at.desc()).first()
        if call_log:
            call_log.call_status = status
            db.commit()

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Vonage event error: {e}")
        return {"status": "error", "message": str(e)}
