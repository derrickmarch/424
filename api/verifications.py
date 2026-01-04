"""
API routes for account verification management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from services.verification_service import VerificationService
from services.scheduler_service import scheduler_service
from config import settings
from schemas import (
    AccountVerificationCreate,
    AccountVerificationResponse,
    BatchStartRequest,
    SystemStats,
    ScheduleStatus
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verifications", tags=["verifications"]) 


@router.post("/", response_model=AccountVerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    verification_data: AccountVerificationCreate,
    db: Session = Depends(get_db)
):
    """Create a new account verification request."""
    try:
        service = VerificationService(db)
        verification = service.create_verification(verification_data)
        return verification
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[AccountVerificationResponse])
def list_verifications(
    status_filter: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List verifications with optional status filter."""
    try:
        from models import AccountVerification, VerificationStatus
        
        query = db.query(AccountVerification)
        
        if status_filter:
            try:
                status_enum = VerificationStatus(status_filter)
                query = query.filter(AccountVerification.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        
        verifications = query.order_by(AccountVerification.created_at.desc()).limit(limit).all()
        return verifications
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing verifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/incomplete", response_model=List[AccountVerificationResponse])
def list_incomplete(
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """List all uncompleted verifications (pending, calling, needs_human)."""
    try:
        from models import AccountVerification, VerificationStatus
        incomplete_statuses = [
            VerificationStatus.PENDING,
            VerificationStatus.CALLING,
            VerificationStatus.NEEDS_HUMAN,
        ]
        verifications = (
            db.query(AccountVerification)
            .filter(AccountVerification.status.in_(incomplete_statuses))
            .order_by(AccountVerification.created_at.desc())
            .limit(limit)
            .all()
        )
        return verifications
    except Exception as e:
        logger.error(f"Error listing incomplete verifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{verification_id}", response_model=AccountVerificationResponse)
def get_verification(
    verification_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific verification by ID."""
    try:
        service = VerificationService(db)
        verification = service.get_verification(verification_id)
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        return verification
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/summary", response_model=SystemStats)
def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    try:
        service = VerificationService(db)
        stats = service.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch/start")
async def start_batch(
    request: BatchStartRequest,
    db: Session = Depends(get_db)
):
    """Start a batch verification process."""
    try:
        from services.call_orchestrator import CallOrchestrator
        
        orchestrator = CallOrchestrator(db)
        
        # Get pending verifications
        pending = orchestrator.verification_service.get_pending_verifications(
            limit=request.max_verifications
        )
        
        if not pending:
            return {
                "message": "No pending verifications to process",
                "verifications_queued": 0
            }
        
        # Start batch processing in background
        import asyncio
        asyncio.create_task(orchestrator.process_batch(max_verifications=request.max_verifications))
        
        return {
            "message": f"Batch processing started",
            "verifications_queued": len(pending)
        }
    
    except Exception as e:
        logger.error(f"Error starting batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{verification_id}", response_model=AccountVerificationResponse)
def update_verification(
    verification_id: str,
    verification_data: AccountVerificationCreate,
    db: Session = Depends(get_db)
):
    """Update an existing verification."""
    try:
        from models import AccountVerification
        
        verification = db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        # Update fields
        verification.customer_name = verification_data.customer_name
        verification.customer_phone = verification_data.customer_phone
        verification.company_name = verification_data.company_name
        verification.company_phone = verification_data.company_phone
        verification.customer_email = verification_data.customer_email
        verification.customer_address = verification_data.customer_address
        verification.account_number = verification_data.account_number
        verification.customer_date_of_birth = verification_data.customer_date_of_birth
        verification.customer_ssn_last4 = verification_data.customer_ssn_last4
        verification.customer_ssn_full = verification_data.customer_ssn_full
        verification.additional_customer_info = verification_data.additional_customer_info
        verification.verification_instruction = verification_data.verification_instruction
        verification.information_to_collect = verification_data.information_to_collect
        verification.priority = verification_data.priority if hasattr(verification_data, 'priority') and verification_data.priority is not None else verification.priority
        
        db.commit()
        db.refresh(verification)
        
        logger.info(f"Verification {verification_id} updated successfully")
        return verification
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{verification_id}")
def delete_verification(
    verification_id: str,
    db: Session = Depends(get_db)
):
    """Delete a verification and its associated data."""
    try:
        from models import AccountVerification, CallLog
        
        verification = db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        # Delete associated call logs first
        db.query(CallLog).filter(
            CallLog.verification_id == verification.verification_id
        ).delete()
        
        # Delete the verification
        db.delete(verification)
        db.commit()
        
        logger.info(f"Verification {verification_id} deleted successfully")
        return {"message": f"Verification {verification_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting verification: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{verification_id}/clear")
def clear_verification(
    verification_id: str,
    db: Session = Depends(get_db)
):
    """Manually retry a failed verification."""
    try:
        from models import AccountVerification, VerificationStatus
        
        verification = db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        # Reset to pending
        verification.status = VerificationStatus.PENDING
        db.commit()
        
        return {"message": f"Verification {verification_id} reset to pending"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying verification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/schedule/status", response_model=ScheduleStatus)
def get_schedule_status(db: Session = Depends(get_db)):
    """Get the status of the automatic calling schedule."""
    try:
        from models import CallSchedule
        
        schedule = db.query(CallSchedule).order_by(
            CallSchedule.created_at.desc()
        ).first()
        
        if not schedule:
            return ScheduleStatus(
                is_running=False,
                last_run_at=None,
                next_run_at=None,
                total_processed=0,
                total_successful=0,
                total_failed=0
            )
        
        return ScheduleStatus(
            is_running=schedule.is_running,
            last_run_at=schedule.last_run_at,
            next_run_at=schedule.next_run_at,
            total_processed=schedule.verifications_processed,
            total_successful=schedule.verifications_successful,
            total_failed=schedule.verifications_failed
        )
    
    except Exception as e:
        logger.error(f"Error getting schedule status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/schedule/trigger")
async def trigger_schedule_now():
    """Trigger the scheduled batch immediately (doesn't wait for next interval)."""
    try:
        import asyncio
        from database import get_db_context
        from services.call_orchestrator import CallOrchestrator
        from services.batch_monitor import batch_monitor
        from models import AccountVerification, VerificationStatus
        
        logger.info("✅ Trigger batch endpoint called successfully")
        
        # Get pending verifications count
        with get_db_context() as db:
            pending_count = db.query(AccountVerification).filter(
                AccountVerification.status == VerificationStatus.PENDING
            ).limit(settings.batch_size_per_loop).count()
        
        if pending_count == 0:
            return {
                "message": "No pending verifications to process",
                "batch_id": None,
                "status": "idle"
            }
        
        # Create batch tracking
        batch_id = batch_monitor.create_batch(
            total_count=pending_count,
            triggered_by="manual_trigger"
        )
        batch_monitor.add_log(batch_id, "info", f"Batch started with {pending_count} verifications")
        
        # Define background task
        async def run_batch_task():
            try:
                batch_monitor.add_log(batch_id, "info", "Starting batch processing...")
                
                with get_db_context() as db_session:
                    orchestrator = CallOrchestrator(db_session)
                    processed, successful, failed = await orchestrator.process_batch(
                        max_verifications=settings.batch_size_per_loop
                    )
                    
                    batch_monitor.update_progress(batch_id, processed, successful, failed)
                    batch_monitor.add_log(batch_id, "success", f"Batch completed: {processed} processed, {successful} successful, {failed} failed")
                    batch_monitor.complete_batch(batch_id)
                    
            except Exception as batch_error:
                logger.error(f"❌ Batch processing error: {batch_error}", exc_info=True)
                batch_monitor.add_log(batch_id, "error", f"Batch error: {str(batch_error)}")
                batch_monitor.stop_batch(batch_id)
        
        # Start background task
        asyncio.create_task(run_batch_task())
        logger.info(f"✅ Batch {batch_id} created and started")
        
        return {
            "message": "Batch processing triggered successfully", 
            "batch_id": batch_id,
            "status": "running",
            "total": pending_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error in trigger endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trigger error: {str(e)}")
