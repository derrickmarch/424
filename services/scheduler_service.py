"""
Scheduler service for automatic looping calls.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from database import get_db_context
from services.call_orchestrator import CallOrchestrator
from models import CallSchedule
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing automatic calling schedule."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def run_scheduled_calls(self):
        """Execute scheduled call batch."""
        logger.info("Starting scheduled call batch...")
        
        with get_db_context() as db:
            # Check if already running
            schedule = db.query(CallSchedule).order_by(
                CallSchedule.created_at.desc()
            ).first()
            
            if schedule and schedule.is_running:
                logger.warning("Previous batch still running, skipping this iteration")
                return
            
            # Mark as running
            if not schedule:
                schedule = CallSchedule(is_running=True)
                db.add(schedule)
            else:
                schedule.is_running = True
            db.commit()
            
            try:
                # Create orchestrator and process batch
                orchestrator = CallOrchestrator(db)
                processed, successful, failed = await orchestrator.process_batch(
                    max_verifications=settings.batch_size_per_loop
                )
                
                # Update schedule
                orchestrator.update_schedule(processed, successful, failed)
                
                logger.info(f"Scheduled batch completed: {processed} processed, {successful} successful, {failed} failed")
                
            except Exception as e:
                logger.error(f"Error in scheduled batch: {e}")
                if schedule:
                    schedule.is_running = False
                    db.commit()
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        if not settings.enable_auto_calling:
            logger.info("Auto-calling is disabled in configuration")
            return
        
        logger.info(f"Starting scheduler with {settings.call_loop_interval_minutes} minute interval")
        
        # Add job to scheduler
        self.scheduler.add_job(
            self.run_scheduled_calls,
            trigger=IntervalTrigger(minutes=settings.call_loop_interval_minutes),
            id='scheduled_calls',
            name='Scheduled Account Verification Calls',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler not running")
            return
        
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Scheduler stopped")
    
    def get_next_run_time(self) -> datetime:
        """Get the next scheduled run time."""
        job = self.scheduler.get_job('scheduled_calls')
        if job:
            return job.next_run_time
        return None
    
    def trigger_now(self):
        """Trigger a batch run immediately."""
        logger.info("Triggering immediate batch run...")
        
        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
            # If we have a loop, create task
            loop.create_task(self.run_scheduled_calls())
        except RuntimeError:
            # No running loop, run it directly using asyncio.run
            logger.info("No running event loop, executing synchronously...")
            asyncio.run(self.run_scheduled_calls())


# Global scheduler instance
scheduler_service = SchedulerService()
