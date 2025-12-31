"""
Batch monitoring service for real-time tracking and control.
"""
from datetime import datetime
from typing import Optional, Dict, List
import uuid
import logging

logger = logging.getLogger(__name__)


class BatchMonitor:
    """Singleton service to monitor and control batch processing."""
    
    def __init__(self):
        self.current_batch_id: Optional[str] = None
        self.should_pause = False
        self.should_stop = False
        self._listeners = []  # WebSocket connections
    
    def create_batch(self, total_count: int, triggered_by: str = None) -> str:
        """Create a new batch process."""
        from database import get_db_context
        from models import BatchProcess, BatchStatus
        
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        with get_db_context() as db:
            batch = BatchProcess(
                batch_id=batch_id,
                status=BatchStatus.RUNNING,
                total_verifications=total_count,
                started_at=datetime.utcnow(),
                triggered_by=triggered_by,
                logs=[]
            )
            db.add(batch)
            db.commit()
        
        self.current_batch_id = batch_id
        self.should_pause = False
        self.should_stop = False
        
        logger.info(f"Created batch {batch_id} with {total_count} verifications")
        return batch_id
    
    def update_progress(self, batch_id: str, processed: int, successful: int, failed: int):
        """Update batch progress."""
        from database import get_db_context
        from models import BatchProcess
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.processed_count = processed
                batch.successful_count = successful
                batch.failed_count = failed
                batch.updated_at = datetime.utcnow()
                db.commit()
                
                # Notify listeners
                self._notify_listeners({
                    "type": "progress",
                    "batch_id": batch_id,
                    "processed": processed,
                    "successful": successful,
                    "failed": failed,
                    "total": batch.total_verifications
                })
    
    def set_current_call(self, batch_id: str, verification_id: str, call_sid: str, 
                        customer_name: str, company_name: str):
        """Update current call information."""
        from database import get_db_context
        from models import BatchProcess
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.current_verification_id = verification_id
                batch.current_call_sid = call_sid
                batch.current_customer_name = customer_name
                batch.current_company_name = company_name
                db.commit()
                
                # Notify listeners
                self._notify_listeners({
                    "type": "current_call",
                    "batch_id": batch_id,
                    "verification_id": verification_id,
                    "call_sid": call_sid,
                    "customer_name": customer_name,
                    "company_name": company_name
                })
    
    def add_log(self, batch_id: str, level: str, message: str):
        """Add a log entry to the batch."""
        from database import get_db_context
        from models import BatchProcess
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                logs = batch.logs or []
                logs.append(log_entry)
                batch.logs = logs
                db.commit()
                
                # Notify listeners
                self._notify_listeners({
                    "type": "log",
                    "batch_id": batch_id,
                    "log": log_entry
                })
    
    def update_transcript(self, batch_id: str, transcript: str):
        """Update live transcript."""
        from database import get_db_context
        from models import BatchProcess
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.live_transcript = transcript
                db.commit()
                
                # Notify listeners
                self._notify_listeners({
                    "type": "transcript",
                    "batch_id": batch_id,
                    "transcript": transcript
                })
    
    def pause_batch(self, batch_id: str):
        """Pause the batch."""
        from database import get_db_context
        from models import BatchProcess, BatchStatus
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.status = BatchStatus.PAUSED
                batch.paused_at = datetime.utcnow()
                db.commit()
        
        self.should_pause = True
        logger.info(f"Paused batch {batch_id}")
        
        self._notify_listeners({
            "type": "status",
            "batch_id": batch_id,
            "status": "paused"
        })
    
    def resume_batch(self, batch_id: str):
        """Resume the batch."""
        from database import get_db_context
        from models import BatchProcess, BatchStatus
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.status = BatchStatus.RUNNING
                batch.paused_at = None
                db.commit()
        
        self.should_pause = False
        logger.info(f"Resumed batch {batch_id}")
        
        self._notify_listeners({
            "type": "status",
            "batch_id": batch_id,
            "status": "running"
        })
    
    def stop_batch(self, batch_id: str):
        """Stop the batch."""
        from database import get_db_context
        from models import BatchProcess, BatchStatus
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.status = BatchStatus.STOPPED
                batch.completed_at = datetime.utcnow()
                db.commit()
        
        self.should_stop = True
        logger.info(f"Stopped batch {batch_id}")
        
        self._notify_listeners({
            "type": "status",
            "batch_id": batch_id,
            "status": "stopped"
        })
    
    def complete_batch(self, batch_id: str):
        """Mark batch as completed."""
        from database import get_db_context
        from models import BatchProcess, BatchStatus
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                batch.status = BatchStatus.COMPLETED
                batch.completed_at = datetime.utcnow()
                db.commit()
        
        self.current_batch_id = None
        logger.info(f"Completed batch {batch_id}")
        
        self._notify_listeners({
            "type": "status",
            "batch_id": batch_id,
            "status": "completed"
        })
    
    def get_status(self, batch_id: str) -> Optional[Dict]:
        """Get current batch status."""
        from database import get_db_context
        from models import BatchProcess
        
        with get_db_context() as db:
            batch = db.query(BatchProcess).filter(BatchProcess.batch_id == batch_id).first()
            if batch:
                return {
                    "batch_id": batch.batch_id,
                    "status": batch.status.value,
                    "total": batch.total_verifications,
                    "processed": batch.processed_count,
                    "successful": batch.successful_count,
                    "failed": batch.failed_count,
                    "current_verification_id": batch.current_verification_id,
                    "current_call_sid": batch.current_call_sid,
                    "current_customer_name": batch.current_customer_name,
                    "current_company_name": batch.current_company_name,
                    "live_transcript": batch.live_transcript,
                    "logs": batch.logs or [],
                    "started_at": batch.started_at.isoformat() if batch.started_at else None,
                    "completed_at": batch.completed_at.isoformat() if batch.completed_at else None
                }
        return None
    
    def add_listener(self, callback):
        """Add a WebSocket listener."""
        self._listeners.append(callback)
    
    def remove_listener(self, callback):
        """Remove a WebSocket listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, data: Dict):
        """Notify all connected WebSocket listeners."""
        for listener in self._listeners:
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")


# Global batch monitor instance
batch_monitor = BatchMonitor()
