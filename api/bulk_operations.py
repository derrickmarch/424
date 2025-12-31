"""
Bulk operations API for efficient batch processing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from typing import List
from pydantic import BaseModel
import structlog
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter(prefix="/api/bulk", tags=["Bulk Operations"])


class BulkDeleteRequest(BaseModel):
    verification_ids: List[str]


class BulkRetryRequest(BaseModel):
    verification_ids: List[str]


class BulkStatusUpdateRequest(BaseModel):
    verification_ids: List[str]
    status: str


class BulkAssignRequest(BaseModel):
    verification_ids: List[str]
    priority: int


@router.post("/delete")
async def bulk_delete(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple verifications at once.
    """
    try:
        from models import AccountVerification, CallLog
        
        deleted_count = 0
        errors = []
        
        for verification_id in request.verification_ids:
            try:
                verification = db.query(AccountVerification).filter(
                    AccountVerification.verification_id == verification_id
                ).first()
                
                if verification:
                    # Delete call logs
                    db.query(CallLog).filter(
                        CallLog.verification_id == verification.id
                    ).delete()
                    
                    # Delete verification
                    db.delete(verification)
                    deleted_count += 1
                else:
                    errors.append(f"{verification_id}: Not found")
            
            except Exception as e:
                errors.append(f"{verification_id}: {str(e)}")
        
        db.commit()
        
        logger.info(f"🗑️ Bulk delete: {deleted_count} deleted, {len(errors)} errors")
        
        return {
            "success": True,
            "deleted": deleted_count,
            "errors": errors,
            "message": f"Successfully deleted {deleted_count} verifications"
        }
    
    except Exception as e:
        logger.error(f"Bulk delete error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry")
async def bulk_retry(
    request: BulkRetryRequest,
    db: Session = Depends(get_db)
):
    """
    Reset multiple verifications to pending for retry.
    """
    try:
        from models import AccountVerification, VerificationStatus
        
        reset_count = 0
        errors = []
        
        for verification_id in request.verification_ids:
            try:
                verification = db.query(AccountVerification).filter(
                    AccountVerification.verification_id == verification_id
                ).first()
                
                if verification:
                    verification.status = VerificationStatus.PENDING
                    verification.last_attempt_at = None
                    reset_count += 1
                else:
                    errors.append(f"{verification_id}: Not found")
            
            except Exception as e:
                errors.append(f"{verification_id}: {str(e)}")
        
        db.commit()
        
        logger.info(f"🔄 Bulk retry: {reset_count} reset, {len(errors)} errors")
        
        return {
            "success": True,
            "reset": reset_count,
            "errors": errors,
            "message": f"Successfully reset {reset_count} verifications for retry"
        }
    
    except Exception as e:
        logger.error(f"Bulk retry error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/priority")
async def bulk_set_priority(
    request: BulkAssignRequest,
    db: Session = Depends(get_db)
):
    """
    Set priority for multiple verifications.
    """
    try:
        from models import AccountVerification
        
        updated_count = 0
        errors = []
        
        for verification_id in request.verification_ids:
            try:
                verification = db.query(AccountVerification).filter(
                    AccountVerification.verification_id == verification_id
                ).first()
                
                if verification:
                    verification.priority = request.priority
                    updated_count += 1
                else:
                    errors.append(f"{verification_id}: Not found")
            
            except Exception as e:
                errors.append(f"{verification_id}: {str(e)}")
        
        db.commit()
        
        logger.info(f"⭐ Bulk priority: {updated_count} updated, {len(errors)} errors")
        
        return {
            "success": True,
            "updated": updated_count,
            "errors": errors,
            "message": f"Successfully updated priority for {updated_count} verifications"
        }
    
    except Exception as e:
        logger.error(f"Bulk priority error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def bulk_export(
    verification_ids: List[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export verifications to CSV format.
    """
    try:
        from models import AccountVerification
        import csv
        from io import StringIO
        
        query = db.query(AccountVerification)
        
        if verification_ids:
            query = query.filter(AccountVerification.verification_id.in_(verification_ids))
        
        verifications = query.all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Verification ID', 'Customer Name', 'Account Number', 
            'Phone Number', 'Company', 'Status', 'Account Exists',
            'Priority', 'Attempts', 'Created At', 'Last Attempt'
        ])
        
        # Data
        for v in verifications:
            writer.writerow([
                v.verification_id,
                v.customer_name,
                v.account_number,
                v.customer_phone,
                v.company_name,
                v.status.value if v.status else '',
                'Yes' if v.account_exists else 'No' if v.account_exists is False else 'Unknown',
                v.priority,
                v.attempt_count,
                v.created_at.isoformat() if v.created_at else '',
                v.last_attempt_at.isoformat() if v.last_attempt_at else ''
            ])
        
        csv_content = output.getvalue()
        
        from fastapi.responses import StreamingResponse
        from io import BytesIO
        
        return StreamingResponse(
            BytesIO(csv_content.encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=verifications_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    except Exception as e:
        logger.error(f"Bulk export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
