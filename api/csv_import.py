"""
API routes for CSV import/export functionality.
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from services.verification_service import VerificationService
from schemas import AccountVerificationCreate
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/csv", tags=["csv"])


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import account verifications from a CSV file.
    
    Expected columns:
    - verification_id
    - customer_name
    - customer_phone
    - company_name
    - company_phone
    - customer_email (optional)
    - customer_address (optional)
    - account_number (optional)
    - verification_instruction (optional)
    - priority (optional, default 0)
    """
    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = [
            'verification_id',
            'customer_name',
            'customer_phone',
            'company_name',
            'company_phone'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process each row
        service = VerificationService(db)
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for idx, row in df.iterrows():
            try:
                # Get optional fields
                customer_email = str(row.get('customer_email')) if 'customer_email' in df.columns and pd.notna(row.get('customer_email')) else None
                customer_address = str(row.get('customer_address')) if 'customer_address' in df.columns and pd.notna(row.get('customer_address')) else None
                account_number = str(row.get('account_number')) if 'account_number' in df.columns and pd.notna(row.get('account_number')) else None
                verification_instruction = str(row.get('verification_instruction')) if 'verification_instruction' in df.columns and pd.notna(row.get('verification_instruction')) else None
                priority = int(row.get('priority', 0)) if 'priority' in df.columns else 0
                
                # Create verification
                verification_data = AccountVerificationCreate(
                    verification_id=str(row['verification_id']),
                    customer_name=str(row['customer_name']),
                    customer_phone=str(row['customer_phone']),
                    company_name=str(row['company_name']),
                    company_phone=str(row['company_phone']),
                    customer_email=customer_email,
                    customer_address=customer_address,
                    account_number=account_number,
                    verification_instruction=verification_instruction,
                    priority=priority
                )
                
                service.create_verification(verification_data)
                results['success'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Row {idx + 2}: {str(e)}")
                logger.warning(f"Failed to import row {idx + 2}: {e}")
        
        return {
            'message': f"Import completed: {results['success']} successful, {results['failed']} failed",
            'details': results
        }
    
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing CSV: {str(e)}")


@router.get("/export")
def export_csv(
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """Export verifications to a CSV file."""
    try:
        from models import AccountVerification, VerificationStatus
        
        query = db.query(AccountVerification)
        
        if status_filter:
            try:
                status_enum = VerificationStatus(status_filter)
                query = query.filter(AccountVerification.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        
        verifications = query.all()
        
        if not verifications:
            raise HTTPException(status_code=404, detail="No verifications to export")
        
        # Convert to DataFrame
        data = []
        for v in verifications:
            data.append({
                'verification_id': v.verification_id,
                'customer_name': v.customer_name,
                'customer_phone': v.customer_phone,
                'company_name': v.company_name,
                'company_phone': v.company_phone,
                'customer_email': v.customer_email or '',
                'account_number': v.account_number or '',
                'status': v.status.value,
                'account_exists': v.account_exists if v.account_exists is not None else '',
                'call_outcome': v.call_outcome.value if v.call_outcome else '',
                'call_summary': v.call_summary or '',
                'attempt_count': v.attempt_count,
                'created_at': v.created_at.isoformat() if v.created_at else '',
                'completed_at': v.completed_at.isoformat() if v.completed_at else '',
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=account_verifications_export.csv"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting CSV: {str(e)}")


@router.get("/template")
def download_template():
    """Download a CSV template for importing verifications."""
    template_data = {
        'verification_id': ['ver_001', 'ver_002'],
        'customer_name': ['John Doe', 'Jane Smith'],
        'customer_phone': ['+12125551234', '+13105559876'],
        'company_name': ['Utility Company ABC', 'Insurance Company XYZ'],
        'company_phone': ['+18005551234', '+18005559876'],
        'customer_email': ['john.doe@email.com', 'jane.smith@email.com'],
        'customer_address': ['123 Main St, New York, NY', '456 Oak Ave, Los Angeles, CA'],
        'account_number': ['ACC123456', 'POL789012'],
        'verification_instruction': ['Check if account is active', 'Verify policy status'],
        'priority': [0, 1]
    }
    
    df = pd.DataFrame(template_data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=account_verification_template.csv"
        }
    )
