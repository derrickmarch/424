"""
Database initialization script.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database."""
    logger.info(f"Initializing database: {settings.database_url}")
    
    try:
        init_db()
        logger.info("Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - account_verifications")
        logger.info("  - call_logs")
        logger.info("  - blocklist")
        logger.info("  - call_schedules")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
