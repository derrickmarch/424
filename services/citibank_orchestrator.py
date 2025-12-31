"""
Call orchestrator for Citibank verification workflow.
Handles batch processing and record rotation logic.
"""
from sqlalchemy.orm import Session
from models import CustomerRecord, AccountStatus, SystemSettings
from services.citibank_agent_service import citibank_agent
from services.twilio_service import twilio_service
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class CitibankCallOrchestrator:
    """Orchestrates the Citibank verification calls with record rotation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.current_batch: List[CustomerRecord] = []
        self.current_index = 0
    
    def get_citibank_phone_number(self) -> str:
        """Get the Citibank phone number from settings."""
        setting = self.db.query(SystemSettings).filter(
            SystemSettings.setting_key == "citibank_phone_number"
        ).first()
        
        # Default Citibank customer service number
        default_number = "+18005742847"
        
        return setting.setting_value if setting else default_number
    
    def get_accounts_per_call(self) -> int:
        """Get the accounts per call setting."""
        setting = self.db.query(SystemSettings).filter(
            SystemSettings.setting_key == "accounts_per_call"
        ).first()
        
        return int(setting.setting_value) if setting else 2
    
    def get_next_unchecked_record(self) -> Optional[CustomerRecord]:
        """
        Get the next unchecked record to verify.
        
        Returns:
            CustomerRecord or None if no more records
        """
        record = self.db.query(CustomerRecord).filter(
            CustomerRecord.status == AccountStatus.UNCHECKED
        ).order_by(
            CustomerRecord.priority.desc(),  # Higher priority first
            CustomerRecord.record_id.asc()   # Then by ID
        ).first()
        
        return record
    
    def move_to_next_record(self, current_record: CustomerRecord) -> Optional[CustomerRecord]:
        """
        Move to the next unchecked record (CASE 1: when SSN fails).
        
        Args:
            current_record: The current record that failed
        
        Returns:
            Next unchecked record or None
        """
        # Mark current as checking
        current_record.status = AccountStatus.CHECKING
        current_record.attempt_count += 1
        current_record.last_attempt_at = datetime.utcnow()
        self.db.commit()
        
        # Get next unchecked record
        next_record = self.get_next_unchecked_record()
        
        if next_record:
            logger.info(f"Moving from record {current_record.record_id} to {next_record.record_id}")
            return next_record
        else:
            logger.info("No more unchecked records available")
            return None
    
    def mark_record_valid(self, record: CustomerRecord, notes: str = ""):
        """
        Mark a record as VALID (CASE 3: Account found).
        
        Args:
            record: The customer record
            notes: Additional notes about the verification
        """
        record.status = AccountStatus.VALID
        record.verified_at = datetime.utcnow()
        record.verification_result = notes or "Account found - Citibank requested additional verification"
        self.db.commit()
        logger.info(f"Record {record.record_id} marked as VALID")
    
    def mark_record_invalid(self, record: CustomerRecord, notes: str = ""):
        """
        Mark a record as INVALID (CASE 2: No account found).
        
        Args:
            record: The customer record
            notes: Additional notes about the verification
        """
        record.status = AccountStatus.INVALID
        record.verified_at = datetime.utcnow()
        record.verification_result = notes or "No account found - Both SSN and card number failed"
        self.db.commit()
        logger.info(f"Record {record.record_id} marked as INVALID")
    
    def mark_record_failed(self, record: CustomerRecord, error: str = ""):
        """
        Mark a record as FAILED (CASE 4: Error occurred).
        
        Args:
            record: The customer record
            error: Error message
        """
        record.status = AccountStatus.FAILED
        record.verification_result = f"Call failed: {error}"
        record.attempt_count += 1
        record.last_attempt_at = datetime.utcnow()
        self.db.commit()
        logger.error(f"Record {record.record_id} marked as FAILED: {error}")
    
    def get_records_for_multi_check(self, max_records: int = 2) -> List[CustomerRecord]:
        """
        Get multiple unchecked records to verify in a single call.
        
        Args:
            max_records: Maximum number of records to check (default 2 to avoid suspicion)
        
        Returns:
            List of CustomerRecord objects
        """
        records = self.db.query(CustomerRecord).filter(
            CustomerRecord.status == AccountStatus.UNCHECKED
        ).order_by(
            CustomerRecord.priority.desc(),
            CustomerRecord.record_id.asc()
        ).limit(max_records).all()
        
        return records
    
    async def process_single_record(self, record: CustomerRecord) -> dict:
        """
        Process a single customer record through the Citibank verification.
        
        Args:
            record: CustomerRecord to verify
        
        Returns:
            Dictionary with verification results
        """
        try:
            logger.info(f"Processing record {record.record_id}: SSN={record.ssn}, Card={record.credit_card_number}")
            
            # Mark as checking
            record.status = AccountStatus.CHECKING
            record.attempt_count += 1
            record.last_attempt_at = datetime.utcnow()
            self.db.commit()
            
            # Generate call script
            script = citibank_agent.generate_call_script(
                ssn=record.ssn,
                credit_card=record.credit_card_number
            )
            
            # TODO: Integrate with Twilio to make actual call
            # Get phone number from settings
            citibank_number = self.get_citibank_phone_number()
            logger.info(f"Would call {citibank_number} for verification")
            
            # For now, use simulation
            conversation, result = citibank_agent.simulate_call({
                'ssn': record.ssn,
                'credit_card_number': record.credit_card_number,
                'name': record.customer_name
            })
            
            # Process result based on case
            status = result.get('status')
            case = result.get('case')
            notes = result.get('notes', '')
            
            if status == 'valid':  # CASE 3
                self.mark_record_valid(record, notes)
                return {
                    'success': True,
                    'record_id': record.record_id,
                    'status': 'valid',
                    'case': case,
                    'notes': notes
                }
            
            elif status == 'invalid':  # CASE 2
                self.mark_record_invalid(record, notes)
                return {
                    'success': True,
                    'record_id': record.record_id,
                    'status': 'invalid',
                    'case': case,
                    'notes': notes
                }
            
            elif status == 'trying_card':  # CASE 1 - move to next
                next_record = self.move_to_next_record(record)
                if next_record:
                    return await self.process_single_record(next_record)
                else:
                    self.mark_record_invalid(record, "No more records to try")
                    return {
                        'success': False,
                        'record_id': record.record_id,
                        'status': 'invalid',
                        'case': 1,
                        'notes': 'SSN failed, no more records available'
                    }
            
            else:  # CASE 4 - failed
                self.mark_record_failed(record, notes)
                return {
                    'success': False,
                    'record_id': record.record_id,
                    'status': 'failed',
                    'case': case,
                    'error': notes
                }
        
        except Exception as e:
            logger.error(f"Error processing record {record.record_id}: {e}")
            self.mark_record_failed(record, str(e))
            return {
                'success': False,
                'record_id': record.record_id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def process_multiple_records_single_call(self, records: List[CustomerRecord]) -> List[dict]:
        """
        Process multiple records in a SINGLE call to save time and money.
        This is more efficient - verify 2 accounts per call instead of 2 separate calls.
        
        Args:
            records: List of CustomerRecord objects (max 2 recommended)
        
        Returns:
            List of verification result dictionaries
        """
        if not records:
            return []
        
        if len(records) > 2:
            logger.warning(f"Processing {len(records)} accounts in single call - may raise suspicion")
        
        results = []
        
        try:
            logger.info(f"Processing {len(records)} records in SINGLE call to save time/money")
            
            for i, record in enumerate(records):
                logger.info(f"  Account {i+1}/{len(records)}: Record {record.record_id}")
                
                # Mark as checking
                record.status = AccountStatus.CHECKING
                record.attempt_count += 1
                record.last_attempt_at = datetime.utcnow()
                self.db.commit()
                
                # Generate script for this account
                script = citibank_agent.generate_call_script(
                    ssn=record.ssn,
                    credit_card=record.credit_card_number
                )
                
                # TODO: Integrate with Twilio - pass all records to make one call
                # For now, simulate each account
                conversation, result = citibank_agent.simulate_call({
                    'ssn': record.ssn,
                    'credit_card_number': record.credit_card_number,
                    'name': record.customer_name
                })
                
                # Process result
                status = result.get('status')
                case = result.get('case')
                notes = result.get('notes', '') + f" [Batch call - account {i+1}/{len(records)}]"
                
                if status == 'valid':
                    self.mark_record_valid(record, notes)
                elif status == 'invalid':
                    self.mark_record_invalid(record, notes)
                else:
                    self.mark_record_failed(record, notes)
                
                results.append({
                    'success': status in ['valid', 'invalid'],
                    'record_id': record.record_id,
                    'status': status,
                    'case': case,
                    'notes': notes
                })
            
            logger.info(f"Multi-account call complete: {len(results)} accounts verified in ONE call")
            return results
            
        except Exception as e:
            logger.error(f"Error in multi-record call: {e}")
            # Mark all remaining records as failed
            for record in records:
                if record.status == AccountStatus.CHECKING:
                    self.mark_record_failed(record, f"Multi-call error: {str(e)}")
            return results
    
    async def process_batch(self, max_records: Optional[int] = None, accounts_per_call: int = 2) -> dict:
        """
        Process a batch of unchecked records.
        Now supports multiple accounts per call for efficiency.
        
        Args:
            max_records: Maximum number of records to process (None = all)
            accounts_per_call: Number of accounts to verify per call (1-2 recommended)
        
        Returns:
            Dictionary with batch processing results
        """
        results = {
            'processed': 0,
            'valid': 0,
            'invalid': 0,
            'failed': 0,
            'calls_made': 0,
            'records': []
        }
        
        # Validate accounts_per_call
        if accounts_per_call < 1:
            accounts_per_call = 1
        elif accounts_per_call > 2:
            logger.warning(f"accounts_per_call={accounts_per_call} may raise suspicion. Recommended: 1-2")
        
        while True:
            # Check if we've hit the limit
            if max_records and results['processed'] >= max_records:
                break
            
            # Get records for multi-check
            remaining = None
            if max_records:
                remaining = max_records - results['processed']
                records_to_get = min(accounts_per_call, remaining)
            else:
                records_to_get = accounts_per_call
            
            if accounts_per_call > 1:
                # Multi-account verification in single call
                batch_records = self.get_records_for_multi_check(records_to_get)
                if not batch_records:
                    logger.info("No more unchecked records to process")
                    break
                
                batch_results = await self.process_multiple_records_single_call(batch_records)
                results['calls_made'] += 1
                
                # Update stats
                for result in batch_results:
                    results['processed'] += 1
                    if result.get('status') == 'valid':
                        results['valid'] += 1
                    elif result.get('status') == 'invalid':
                        results['invalid'] += 1
                    else:
                        results['failed'] += 1
                    results['records'].append(result)
            else:
                # Single account per call (original behavior)
                record = self.get_next_unchecked_record()
                if not record:
                    logger.info("No more unchecked records to process")
                    break
                
                result = await self.process_single_record(record)
                results['calls_made'] += 1
                results['processed'] += 1
                
                if result.get('status') == 'valid':
                    results['valid'] += 1
                elif result.get('status') == 'invalid':
                    results['invalid'] += 1
                else:
                    results['failed'] += 1
                
                results['records'].append(result)
        
        logger.info(f"Batch complete: {results['processed']} accounts processed in {results['calls_made']} calls, "
                   f"{results['valid']} valid, {results['invalid']} invalid, {results['failed']} failed")
        
        return results
