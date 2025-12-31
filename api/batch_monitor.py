"""
API endpoints for batch monitoring and control.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from services.batch_monitor import batch_monitor
from api.auth import get_current_user
from models import User
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch-monitor"])


@router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str, user: User = Depends(get_current_user)):
    """Get current status of a batch."""
    try:
        status = batch_monitor.get_status(batch_id)
        if not status:
            raise HTTPException(status_code=404, detail="Batch not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_batch(user: User = Depends(get_current_user)):
    """Get the currently running batch."""
    try:
        if not batch_monitor.current_batch_id:
            return {"batch_id": None, "status": "idle"}
        
        status = batch_monitor.get_status(batch_monitor.current_batch_id)
        return status or {"batch_id": None, "status": "idle"}
    except Exception as e:
        logger.error(f"Error getting current batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{batch_id}/pause")
async def pause_batch(batch_id: str, user: User = Depends(get_current_user)):
    """Pause a running batch."""
    try:
        batch_monitor.pause_batch(batch_id)
        return {"message": "Batch paused successfully", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Error pausing batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{batch_id}/resume")
async def resume_batch(batch_id: str, user: User = Depends(get_current_user)):
    """Resume a paused batch."""
    try:
        batch_monitor.resume_batch(batch_id)
        return {"message": "Batch resumed successfully", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Error resuming batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{batch_id}/stop")
async def stop_batch(batch_id: str, user: User = Depends(get_current_user)):
    """Stop a running or paused batch."""
    try:
        batch_monitor.stop_batch(batch_id)
        return {"message": "Batch stopped successfully", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Error stopping batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{batch_id}")
async def websocket_endpoint(websocket: WebSocket, batch_id: str):
    """WebSocket endpoint for real-time batch updates."""
    await websocket.accept()
    logger.info(f"WebSocket connected for batch {batch_id}")
    
    # Create a callback to send updates to this WebSocket
    async def send_update(data: dict):
        try:
            if data.get("batch_id") == batch_id:
                await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
    
    # Register listener
    batch_monitor.add_listener(send_update)
    
    try:
        # Send initial status
        status = batch_monitor.get_status(batch_id)
        if status:
            await websocket.send_json({
                "type": "initial",
                "data": status
            })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client can send ping messages to keep connection alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for batch {batch_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove listener
        batch_monitor.remove_listener(send_update)
