from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.verification_service import VerificationService
import logging

router = APIRouter(prefix="/api/plivo", tags=["plivo"]) 
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def plivo_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        metadata = data.get("metadata") or {}
        verification_id = metadata.get("verification_id") or data.get("verification_id")
        status = (data.get("status") or "").lower()
        if not verification_id:
            raise HTTPException(status_code=400, detail="verification_id required")
        service = VerificationService(db)
        v = service.get_verification(verification_id)
        if not v:
            raise HTTPException(status_code=404, detail="Verification not found")
        from schemas import CallOutcome, CallResultSchema
        if status in ("completed", "success"):
            result = CallResultSchema(call_outcome=CallOutcome.NEEDS_HUMAN, verification_status="needs_human", account_exists=False, account_details=None, agent_notes="Plivo: review needed (mock)")
        elif status in ("failed", "busy", "no_answer"):
            result = CallResultSchema(call_outcome=CallOutcome.FAILED, verification_status="failed", account_exists=False, account_details=None, agent_notes=f"Plivo: {status}")
        else:
            return {"status": "ok"}
        service.update_call_result(verification_id=verification_id, result=result, call_summary="Plivo webhook", transcript=None, call_duration=None)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plivo webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
