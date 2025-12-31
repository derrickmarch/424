"""
API routes for customer record management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from services.verification_service import VerificationService
from services.csv_service import CSVService
from models import AccountStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/")
def list_records(
    status_filter: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List customer records with optional status filter."""
    try:
        from models import CustomerRecord
        
        query = db.query(CustomerRecord)
        
        if status_filter:
            try:
                status_enum = AccountStatus(status_filter)
                query = query.filter(CustomerRecord.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        
        records = query.order_by(CustomerRecord.record_id.asc()).limit(limit).all()
        
        return [{
            "record_id": r.record_id,
            "customer_id": r.customer_id,
            "customer_name": r.customer_name,
            "ssn": r.ssn if r.ssn else None,  # Full SSN
            "credit_card_number": r.credit_card_number if r.credit_card_number else None,
            "status": r.status.value,
            "attempt_count": r.attempt_count,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Get verification statistics."""
    try:
        service = VerificationService(db)
        stats = service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch/start")
async def start_batch(
    max_records: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Start batch processing of unchecked records."""
    try:
        from services.call_orchestrator import CitibankCallOrchestrator
        import asyncio
        
        orchestrator = CitibankCallOrchestrator(db)
        
        # Start processing in background
        asyncio.create_task(orchestrator.process_batch(max_records))
        
        return {
            "message": "Batch processing started",
            "max_records": max_records
        }
    
    except Exception as e:
        logger.error(f"Error starting batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/csv/import")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import customer records from CSV."""
    try:
        contents = await file.read()
        result = CSVService.import_from_csv(contents, db)
        
        if result['success']:
            return {
                "message": f"Import completed: {result['imported']} imported, {result['skipped']} skipped",
                "details": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Import failed'))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/csv/export")
def export_csv(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export customer records to CSV."""
    try:
        csv_content = CSVService.export_to_csv(db, status_filter)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=citibank_verification_results.csv"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/csv/template")
def download_template():
    """Download CSV template."""
    try:
        csv_content = CSVService.get_csv_template()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=citibank_verification_template.csv"
            }
        )
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_verification(db: Session = Depends(get_db)):
    """Test verification with sample data (no real call)."""
    try:
        from services.citibank_agent_service import citibank_agent
        
        # Test with sample data
        test_data = {
            'ssn': '424-66-6363',
            'credit_card_number': '1385678881',
            'name': 'Test Customer'
        }
        
        conversation, result = citibank_agent.simulate_call(test_data)
        
        return {
            "message": "Test completed (no real call made)",
            "test_data": test_data,
            "result": result,
            "conversation": conversation
        }
    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    """Get a single customer record by ID."""
    try:
        from models import CustomerRecord
        
        record = db.query(CustomerRecord).filter(CustomerRecord.record_id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        
        return {
            "record_id": record.record_id,
            "customer_id": record.customer_id,
            "customer_name": record.customer_name,
            "ssn": record.ssn if record.ssn else None,
            "credit_card_number": record.credit_card_number,
            "email": record.email,
            "phone": record.phone,
            "address": record.address,
            "status": record.status.value,
            "attempt_count": record.attempt_count,
            "verified_at": record.verified_at.isoformat() if record.verified_at else None,
            "verification_result": record.verification_result,
            "notes": record.notes,
            "priority": record.priority,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting record: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{record_id}")
def update_record(
    record_id: int,
    customer_id: Optional[str] = None,
    customer_name: Optional[str] = None,
    ssn: Optional[str] = None,
    credit_card_number: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update a customer record."""
    try:
        from models import CustomerRecord
        
        record = db.query(CustomerRecord).filter(CustomerRecord.record_id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        
        # Update fields if provided
        if customer_id is not None:
            record.customer_id = customer_id
        if customer_name is not None:
            record.customer_name = customer_name
        if ssn is not None:
            record.ssn = ssn
        if credit_card_number is not None:
            record.credit_card_number = credit_card_number
        if email is not None:
            record.email = email
        if phone is not None:
            record.phone = phone
        if address is not None:
            record.address = address
        if notes is not None:
            record.notes = notes
        if priority is not None:
            record.priority = priority
        
        db.commit()
        db.refresh(record)
        
        logger.info(f"Updated record {record_id}")
        
        return {
            "message": "Record updated successfully",
            "record_id": record.record_id,
            "customer_name": record.customer_name,
            "status": record.status.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating record: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    """Delete a customer record."""
    try:
        from models import CustomerRecord
        
        record = db.query(CustomerRecord).filter(CustomerRecord.record_id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
        
        customer_name = record.customer_name
        db.delete(record)
        db.commit()
        
        logger.info(f"Deleted record {record_id} ({customer_name})")
        
        return {
            "message": "Record deleted successfully",
            "record_id": record_id,
            "customer_name": customer_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
