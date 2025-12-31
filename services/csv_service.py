"""
CSV import/export service for customer records.
"""
import pandas as pd
import io
from typing import Optional
from sqlalchemy.orm import Session
from models import CustomerRecord, AccountStatus
import logging

logger = logging.getLogger(__name__)


class CSVService:
    """Service for importing and exporting customer records via CSV."""
    
    @staticmethod
    def import_from_csv(file_content: bytes, db: Session) -> dict:
        """
        Import customer records from CSV file.
        
        Expected CSV columns:
        - customer_id (optional)
        - customer_name (optional)
        - ssn (required)
        - credit_card_number (required)
        - email (optional)
        - phone (optional)
        - address (optional)
        - notes (optional)
        - status (optional - if already checked)
        
        Args:
            file_content: CSV file content as bytes
            db: Database session
        
        Returns:
            Dict with import results
        """
        try:
            # Read CSV
            df = pd.read_csv(io.BytesIO(file_content))
            
            # Validate required columns
            required_columns = ['ssn', 'credit_card_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f"Missing required columns: {', '.join(missing_columns)}"
                }
            
            results = {
                'success': True,
                'imported': 0,
                'skipped': 0,
                'errors': []
            }
            
            for idx, row in df.iterrows():
                try:
                    # Check if already exists (by SSN or card number)
                    ssn = str(row['ssn']).strip()
                    card = str(row['credit_card_number']).strip()
                    
                    existing = db.query(CustomerRecord).filter(
                        (CustomerRecord.ssn == ssn) | 
                        (CustomerRecord.credit_card_number == card)
                    ).first()
                    
                    if existing:
                        # Update if status is unchecked or failed
                        if existing.status in [AccountStatus.UNCHECKED, AccountStatus.FAILED]:
                            existing.customer_name = str(row.get('customer_name', '')) if 'customer_name' in row else None
                            existing.email = str(row.get('email', '')) if 'email' in row else None
                            existing.phone = str(row.get('phone', '')) if 'phone' in row else None
                            existing.address = str(row.get('address', '')) if 'address' in row else None
                            existing.notes = str(row.get('notes', '')) if 'notes' in row else None
                            results['imported'] += 1
                        else:
                            # Skip if already valid/invalid
                            results['skipped'] += 1
                        continue
                    
                    # Get status from CSV if provided
                    status_value = str(row.get('status', 'unchecked')).lower() if 'status' in row else 'unchecked'
                    try:
                        status = AccountStatus(status_value)
                    except ValueError:
                        status = AccountStatus.UNCHECKED
                    
                    # Create new record
                    record = CustomerRecord(
                        customer_id=str(row.get('customer_id', '')) if 'customer_id' in row else None,
                        customer_name=str(row.get('customer_name', '')) if 'customer_name' in row else None,
                        ssn=ssn,
                        credit_card_number=card,
                        email=str(row.get('email', '')) if 'email' in row else None,
                        phone=str(row.get('phone', '')) if 'phone' in row else None,
                        address=str(row.get('address', '')) if 'address' in row else None,
                        notes=str(row.get('notes', '')) if 'notes' in row else None,
                        status=status,
                        priority=int(row.get('priority', 0)) if 'priority' in row else 0
                    )
                    
                    db.add(record)
                    results['imported'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Row {idx + 2}: {str(e)}")
                    logger.error(f"Error importing row {idx + 2}: {e}")
            
            db.commit()
            
            return results
            
        except Exception as e:
            logger.error(f"CSV import error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def export_to_csv(db: Session, status_filter: Optional[str] = None) -> str:
        """
        Export customer records to CSV.
        
        Args:
            db: Database session
            status_filter: Optional status to filter by
        
        Returns:
            CSV content as string
        """
        query = db.query(CustomerRecord)
        
        if status_filter:
            try:
                status_enum = AccountStatus(status_filter)
                query = query.filter(CustomerRecord.status == status_enum)
            except ValueError:
                pass
        
        records = query.all()
        
        data = []
        for r in records:
            data.append({
                'record_id': r.record_id,
                'customer_id': r.customer_id or '',
                'customer_name': r.customer_name or '',
                'ssn': r.ssn or '',
                'credit_card_number': r.credit_card_number or '',
                'email': r.email or '',
                'phone': r.phone or '',
                'address': r.address or '',
                'status': r.status.value,
                'verification_result': r.verification_result or '',
                'attempt_count': r.attempt_count,
                'verified_at': r.verified_at.isoformat() if r.verified_at else '',
                'notes': r.notes or ''
            })
        
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    
    @staticmethod
    def get_csv_template() -> str:
        """
        Generate a CSV template for import.
        
        Returns:
            CSV template as string
        """
        template_data = {
            'customer_id': ['C001', 'C002'],
            'customer_name': ['John Doe', 'Jane Smith'],
            'ssn': ['424-66-6363', '123-45-6789'],
            'credit_card_number': ['1385678881', '9876543210'],
            'email': ['john@email.com', 'jane@email.com'],
            'phone': ['+12125551234', '+13105559876'],
            'address': ['123 Main St', '456 Oak Ave'],
            'notes': ['', ''],
            'status': ['unchecked', 'unchecked']
        }
        
        df = pd.DataFrame(template_data)
        return df.to_csv(index=False)
