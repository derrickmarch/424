"""
API routes for Twilio webhooks.
"""
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.twilio_service import get_twilio_service
from services.call_orchestrator import CallOrchestrator
from services.verification_service import VerificationService
from schemas import CallContext
from config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])


@router.post("/voice")
async def handle_voice_webhook(
    request: Request,
    verification_id: str,
    db: Session = Depends(get_db)
):
    """
    Handle Twilio voice webhook when call is answered.
    Returns TwiML to start Media Stream.
    """
    try:
        # Get request data
        form_data = await request.form()
        
        # Validate Twilio signature (in production)
        if settings.app_env == "production":
            signature = request.headers.get("X-Twilio-Signature", "")
            url = str(request.url)
            # Note: validate_request needs implementation in twilio_service
            # if not twilio_service.validate_request(dict(form_data), signature, url):
            #     raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
        # Get verification
        service = VerificationService(db)
        verification = service.get_verification(verification_id)
        
        if not verification:
            logger.error(f"Verification {verification_id} not found for voice webhook")
            twilio_service = get_twilio_service(db)
            return Response(
                content=twilio_service.generate_voicemail_twiml(),
                media_type="application/xml"
            )
        
        # Check if this is a voicemail (machine detection)
        answered_by = form_data.get("AnsweredBy")
        if answered_by in ["machine_start", "machine_end_beep", "machine_end_silence"]:
            logger.info(f"Voicemail detected for verification {verification_id}")
            
            # Mark as voicemail
            from schemas import CallResultSchema, CallOutcome
            result = CallResultSchema(
                account_exists=False,
                verification_status="voicemail",
                agent_notes="Reached voicemail",
                call_outcome=CallOutcome.VOICEMAIL,
                follow_up_needed=False
            )
            service.update_call_result(
                verification_id=verification_id,
                result=result,
                call_summary="Reached voicemail at company"
            )
            
            twilio_service = get_twilio_service(db)
            return Response(
                content=twilio_service.generate_voicemail_twiml(),
                media_type="application/xml"
            )
        
        # For now, return simple TwiML since full WebSocket integration needs more setup
        # In production, you'd start a media stream here
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        
        # Simple greeting for testing
        response.say(
            f"Hi! This is an automated assistant calling to verify account information. "
            f"We're checking if you have an account on file for {verification.customer_name}. "
            f"The phone number we have is {verification.customer_phone}. "
            f"Can you confirm if this account exists in your system?",
            voice='Polly.Joanna'
        )
        
        # Gather response
        response.pause(length=3)
        response.say("Thank you for your time. Goodbye.", voice='Polly.Joanna')
        
        logger.info(f"Returning TwiML for verification {verification_id}")
        
        return Response(content=str(response), media_type="application/xml")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice webhook: {e}")
        twilio_service = get_twilio_service(db)
        return Response(
            content=twilio_service.generate_voicemail_twiml(),
            media_type="application/xml"
        )


@router.post("/status-callback")
async def handle_status_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Twilio status callbacks.
    Receives updates about call status.
    """
    try:
        form_data = await request.form()
        
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        
        logger.info(f"Status callback: {call_sid} - {call_status}")
        
        # Update call log
        from models import CallLog
        call_log = db.query(CallLog).filter(
            CallLog.call_sid == call_sid
        ).order_by(CallLog.created_at.desc()).first()
        
        if call_log:
            call_log.call_status = call_status
            
            if call_status == "completed":
                from datetime import datetime
                call_log.completed_at = datetime.utcnow()
                
                call_duration = form_data.get("CallDuration")
                if call_duration:
                    call_log.duration_seconds = int(call_duration)
            
            db.commit()
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error in status callback: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/test-call/{verification_id}")
async def test_call(
    verification_id: str,
    db: Session = Depends(get_db)
):
    """
    Test endpoint to simulate a call without actually calling.
    Useful for development and testing.
    """
    try:
        from services.ai_agent_service import ai_agent_service
        
        service = VerificationService(db)
        verification = service.get_verification(verification_id)
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
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
            attempt_number=verification.attempt_count + 1
        )
        
        # Simulate conversation
        transcript, result, summary = ai_agent_service.simulate_conversation(call_context)
        
        # Update verification
        service.update_call_result(
            verification_id=verification_id,
            result=result,
            call_summary=summary,
            transcript=transcript,
            call_duration=120  # Simulated 2 minutes
        )
        
        return {
            "message": "Test call completed",
            "transcript": transcript,
            "result": result.model_dump(),
            "summary": summary
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test call: {e}")
        raise HTTPException(status_code=500, detail=str(e))
