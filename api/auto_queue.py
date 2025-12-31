"""
API endpoints for automatic verification queue management.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from services.auto_verification_queue import AutoVerificationQueue
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/auto-queue", tags=["Auto Queue"])

# Store active queue processor
active_queue: dict = {}


@router.post("/start")
async def start_auto_queue(
    background_tasks: BackgroundTasks,
    max_verifications: int = None,
    db: Session = Depends(get_db)
):
    """
    Start automatic verification queue processing.
    Processes verifications one by one, hanging up immediately after verification.
    """
    if 'processor' in active_queue and active_queue['processor'].is_running:
        return {
            "success": False,
            "message": "Queue processor already running",
            "current_verification": active_queue['processor'].current_verification_id
        }
    
    try:
        queue = AutoVerificationQueue(db)
        active_queue['processor'] = queue
        
        # Process in background
        async def process():
            return await queue.process_queue(max_verifications)
        
        background_tasks.add_task(process)
        
        logger.info(f"🚀 Started auto queue processor (max: {max_verifications or 'unlimited'})")
        
        return {
            "success": True,
            "message": "Auto queue processing started",
            "max_verifications": max_verifications
        }
    
    except Exception as e:
        logger.error(f"Failed to start auto queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_auto_queue(db: Session = Depends(get_db)):
    """
    Stop the automatic verification queue processor.
    """
    if 'processor' not in active_queue or not active_queue['processor'].is_running:
        return {
            "success": False,
            "message": "No queue processor is currently running"
        }
    
    try:
        queue = active_queue['processor']
        queue.stop_processing()
        
        logger.info("🛑 Stopped auto queue processor")
        
        return {
            "success": True,
            "message": "Auto queue processor stopped"
        }
    
    except Exception as e:
        logger.error(f"Failed to stop auto queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_queue_status(db: Session = Depends(get_db)):
    """
    Get current status of the automatic queue processor.
    """
    if 'processor' not in active_queue:
        return {
            "running": False,
            "current_verification": None,
            "current_call": None
        }
    
    queue = active_queue['processor']
    
    return {
        "running": queue.is_running,
        "current_verification": queue.current_verification_id,
        "current_call": queue.current_call_sid
    }
