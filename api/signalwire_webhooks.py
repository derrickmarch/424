from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.verification_service import VerificationService
import logging

router = APIRouter(prefix="/api/signalwire", tags=["signalwire"]) 
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def signalwire_webhook(request: Request, db: Session = Depends(get_db)):
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
            result = CallResultSchema(call_outcome=CallOutcome.ACCOUNT_NOT_FOUND, verification_status="not_found", account_exists=False, account_details=None, agent_notes="SignalWire: not found (mock)")
        elif status in ("failed", "busy", "no_answer"):
            result = CallResultSchema(call_outcome=CallOutcome.FAILED, verification_status="failed", account_exists=False, account_details=None, agent_notes=f"SignalWire: {status}")
        else:
            return {"status": "ok"}
        service.update_call_result(verification_id=verification_id, result=result, call_summary="SignalWire webhook", transcript=None, call_duration=None)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SignalWire webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
