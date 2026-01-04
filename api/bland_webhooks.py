"""
API routes for Bland AI webhooks.
Bland hosts the agent. We receive final results and status updates here.
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.verification_service import VerificationService
from services.call_orchestrator import CallOrchestrator
from schemas import CallContext, CallOutcome, CallResultSchema
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bland", tags=["bland"]) 


@router.post("/webhook")
async def bland_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Bland webhook events. Expected JSON body with at least:
    - id or call_id
    - status (started, ringing, answered, completed, failed, voicemail, ...)
    - transcript (optional)
    - duration (optional seconds)
    - metadata.verification_id (we pass this when creating the call)
    - optional outcome fields if your Bland flow posts them (e.g., outcome, account_exists)
    """
    try:
        data = await request.json()
        call_id = data.get("id") or data.get("call_id") or data.get("uuid")
        status = (data.get("status") or "").lower()
        metadata = data.get("metadata") or {}
        verification_id = metadata.get("verification_id") or data.get("verification_id")
        transcript = data.get("transcript") or data.get("conversation") or ""
        duration = data.get("duration") or data.get("call_duration")
        outcome = (data.get("outcome") or data.get("result") or "").lower()

        if not verification_id:
            logger.error(f"Bland webhook missing verification_id: {data}")
            raise HTTPException(status_code=400, detail="verification_id required")

        service = VerificationService(db)
        verification = service.get_verification(verification_id)
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")

        # Map Bland statuses/outcomes to our schema
        if status in ("voicemail",):
            result = CallResultSchema(
                call_outcome=CallOutcome.VOICEMAIL,
                verification_status="voicemail",
                account_exists=False,
                account_details=None,
                agent_notes="Reached voicemail",
                follow_up_needed=False,
            )
            summary = f"Reached voicemail at {verification.company_name}"
        elif status in ("failed", "busy", "no_answer"):
            result = CallResultSchema(
                call_outcome=CallOutcome.FAILED,
                verification_status="failed",
                account_exists=False,
                account_details=None,
                agent_notes=f"Call {status}",
                follow_up_needed=True,
            )
            summary = f"Call {status} for {verification.company_name}"
        elif status == "completed":
            # Try to use provided outcome hint; default to needs_human
            if outcome in ("account_found", "verified", "success"):
                result = CallResultSchema(
                    call_outcome=CallOutcome.ACCOUNT_FOUND,
                    verification_status="verified",
                    account_exists=True,
                    account_details={"source": "bland"},
                    agent_notes="Bland agent indicated account exists",
                    follow_up_needed=False,
                )
            elif outcome in ("account_not_found", "not_found"):
                result = CallResultSchema(
                    call_outcome=CallOutcome.ACCOUNT_NOT_FOUND,
                    verification_status="not_found",
                    account_exists=False,
                    account_details=None,
                    agent_notes="Bland agent indicated no account",
                    follow_up_needed=False,
                )
            else:
                result = CallResultSchema(
                    call_outcome=CallOutcome.NEEDS_HUMAN,
                    verification_status="needs_human",
                    account_exists=False,
                    account_details=None,
                    agent_notes="Bland agent requires human review",
                    follow_up_needed=True,
                )
            summary = "Result from Bland agent"
        else:
            # Intermediate statuses; acknowledge only
            return {"status": "ok"}

        # Persist results
        call_duration = int(duration) if duration else None
        service.update_call_result(
            verification_id=verification_id,
            result=result,
            call_summary=summary,
            transcript=transcript or None,
            call_duration=call_duration,
        )

        # Update call log record if present
        try:
            from models import CallLog
            call_log = db.query(CallLog).filter(CallLog.verification_id == verification_id).order_by(CallLog.created_at.desc()).first()
            if call_log:
                call_log.call_status = status or "completed"
                if call_id:
                    call_log.call_sid = call_id
                if call_duration:
                    call_log.duration_seconds = call_duration
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to update CallLog from Bland webhook: {e}")

        return {"status": "updated"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bland webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
