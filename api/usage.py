"""
API endpoints for usage and billing information.
"""
from fastapi import APIRouter, HTTPException
from services.twilio_service import get_twilio_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/twilio")
async def get_twilio_usage():
    """
    Get Twilio account balance and usage statistics.
    
    Returns current balance, currency, and call usage for the current month.
    """
    try:
        twilio_service = get_twilio_service()
        usage_data = twilio_service.get_account_balance()
        return usage_data
    except Exception as e:
        logger.error(f"Error fetching Twilio usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
