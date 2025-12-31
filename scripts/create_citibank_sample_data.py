"""
Create sample data for Citibank verification testing.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import CustomerRecord, AccountStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_data():
    """Create sample customer records for testing."""
    db = SessionLocal()
    
    try:
        # Sample records based on your example
        sample_records = [
            {
                'customer_id': 'C001',
                'customer_name': 'John Doe',
                'ssn': '424-66-6363',
                'credit_card_number': '1385678881',
                'email': 'john.doe@example.com',
                'phone': '+12125551234',
                'status': AccountStatus.UNCHECKED
            },
            {
                'customer_id': 'C002',
                'customer_name': 'Jane Smith',
                'ssn': '123-45-6789',
                'credit_card_number': '9876543210',
                'email': 'jane.smith@example.com',
                'phone': '+13105559876',
                'status': AccountStatus.UNCHECKED
            },
            {
                'customer_id': 'C003',
                'customer_name': 'Bob Johnson',
                'ssn': '555-66-7777',
                'credit_card_number': '4444333322221111',
                'email': 'bob.j@example.com',
                'phone': '+14155558888',
                'status': AccountStatus.UNCHECKED
            }
        ]
        
        for data in sample_records:
            # Check if already exists
            existing = db.query(CustomerRecord).filter(
                CustomerRecord.ssn == data['ssn']
            ).first()
            
            if not existing:
                record = CustomerRecord(**data)
                db.add(record)
                logger.info(f"Created record: {data['customer_name']} - {data['ssn']}")
            else:
                logger.info(f"Record already exists: {data['customer_name']}")
        
        db.commit()
        logger.info("Sample data created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()
