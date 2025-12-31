"""
Create sample account verification data for testing.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db_context
from services.verification_service import VerificationService
from schemas import AccountVerificationCreate
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_verifications():
    """Create sample verifications for testing."""
    
    sample_data = [
        {
            "verification_id": "ver_001",
            "customer_name": "John Smith",
            "customer_phone": "+12125551234",
            "company_name": "City Electric Utility",
            "company_phone": "+18005551234",
            "customer_email": "john.smith@email.com",
            "account_number": "ELEC123456",
            "verification_instruction": "Check if electric account is active",
            "priority": 1
        },
        {
            "verification_id": "ver_002",
            "customer_name": "Maria Garcia",
            "customer_phone": "+13105559876",
            "company_name": "HealthCare Insurance Co",
            "company_phone": "+18005559876",
            "customer_email": "maria.garcia@email.com",
            "account_number": "INS789012",
            "verification_instruction": "Verify insurance policy status",
            "priority": 2
        },
        {
            "verification_id": "ver_003",
            "customer_name": "David Chen",
            "customer_phone": "+16505554567",
            "company_name": "Metro Water Department",
            "company_phone": "+18005554567",
            "customer_email": "david.chen@email.com",
            "account_number": "WAT456789",
            "verification_instruction": "Confirm water service account",
            "priority": 0
        },
        {
            "verification_id": "ver_004",
            "customer_name": "Sarah Johnson",
            "customer_phone": "+17185553456",
            "company_name": "National Bank",
            "company_phone": "+18005553456",
            "customer_email": "sarah.johnson@email.com",
            "account_number": "BNK987654",
            "verification_instruction": "Verify checking account status",
            "priority": 1
        },
        {
            "verification_id": "ver_005",
            "customer_name": "Michael Brown",
            "customer_phone": "+14155552345",
            "company_name": "Cable & Internet Provider",
            "company_phone": "+18005552345",
            "customer_email": "michael.brown@email.com",
            "account_number": "CAB654321",
            "verification_instruction": "Check internet service account",
            "priority": 0
        }
    ]
    
    with get_db_context() as db:
        service = VerificationService(db)
        
        for data in sample_data:
            try:
                verification = AccountVerificationCreate(**data)
                created = service.create_verification(verification)
                logger.info(f"Created verification: {created.verification_id}")
            except Exception as e:
                logger.error(f"Failed to create {data['verification_id']}: {e}")
    
    logger.info(f"Sample data creation completed!")


if __name__ == "__main__":
    create_sample_verifications()
