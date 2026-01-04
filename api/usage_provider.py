"""
Provider-agnostic usage endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.telephony import get_telephony_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/usage", tags=["usage"])

@router.get("/provider")
async def get_provider_usage(db: Session = Depends(get_db)):
    try:
        telephony = get_telephony_service(db)
        usage_data = telephony.get_account_balance()
        return usage_data
    except Exception as e:
        logger.error(f"Error fetching provider usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
