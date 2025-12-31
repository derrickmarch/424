"""
Analytics and reporting API endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from database import get_db
from datetime import datetime, timedelta
from typing import Optional
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard-stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get key metrics for dashboard overview.
    """
    try:
        from models import AccountVerification, CallLog, VerificationStatus
        
        # Total verifications
        total = db.query(func.count(AccountVerification.id)).scalar()
        
        # By status
        pending = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.status == VerificationStatus.PENDING
        ).scalar()
        
        in_progress = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.status == VerificationStatus.IN_PROGRESS
        ).scalar()
        
        completed = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.status == VerificationStatus.COMPLETED
        ).scalar()
        
        failed = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.status == VerificationStatus.FAILED
        ).scalar()
        
        # Account verification results
        verified = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.account_exists == True
        ).scalar()
        
        not_found = db.query(func.count(AccountVerification.id)).filter(
            AccountVerification.account_exists == False
        ).scalar()
        
        # Call statistics
        total_calls = db.query(func.count(CallLog.id)).scalar()
        
        avg_duration = db.query(func.avg(CallLog.duration_seconds)).filter(
            CallLog.duration_seconds.isnot(None)
        ).scalar() or 0
        
        # Today's activity
        today = datetime.now().date()
        calls_today = db.query(func.count(CallLog.id)).filter(
            func.date(CallLog.created_at) == today
        ).scalar()
        
        verified_today = db.query(func.count(AccountVerification.id)).filter(
            func.date(AccountVerification.updated_at) == today,
            AccountVerification.account_exists == True
        ).scalar()
        
        # Success rate
        success_rate = (verified / total * 100) if total > 0 else 0
        
        return {
            "overview": {
                "total_verifications": total,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed
            },
            "results": {
                "verified": verified,
                "not_found": not_found,
                "unknown": total - verified - not_found,
                "success_rate": round(success_rate, 2)
            },
            "calls": {
                "total_calls": total_calls,
                "average_duration_seconds": round(avg_duration, 2),
                "calls_today": calls_today
            },
            "today": {
                "calls_made": calls_today,
                "accounts_verified": verified_today
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            "error": str(e),
            "overview": {},
            "results": {},
            "calls": {},
            "today": {}
        }


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get verification trends over time.
    """
    try:
        from models import AccountVerification, CallLog
        
        # Get daily stats for last N days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            # Calls made
            calls = db.query(func.count(CallLog.id)).filter(
                func.date(CallLog.created_at) == current_date
            ).scalar()
            
            # Verifications completed
            completed = db.query(func.count(AccountVerification.id)).filter(
                func.date(AccountVerification.updated_at) == current_date,
                AccountVerification.account_exists.isnot(None)
            ).scalar()
            
            # Accounts verified
            verified = db.query(func.count(AccountVerification.id)).filter(
                func.date(AccountVerification.updated_at) == current_date,
                AccountVerification.account_exists == True
            ).scalar()
            
            daily_stats.append({
                "date": current_date.isoformat(),
                "calls_made": calls,
                "verifications_completed": completed,
                "accounts_verified": verified
            })
            
            current_date += timedelta(days=1)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "daily_stats": daily_stats
        }
    
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get system performance metrics.
    """
    try:
        from models import AccountVerification, CallLog, CallOutcome
        
        # Average call duration by outcome
        duration_by_outcome = db.query(
            CallLog.call_outcome,
            func.avg(CallLog.duration_seconds).label('avg_duration'),
            func.count(CallLog.id).label('count')
        ).filter(
            CallLog.call_outcome.isnot(None),
            CallLog.duration_seconds.isnot(None)
        ).group_by(CallLog.call_outcome).all()
        
        # Retry statistics
        retry_stats = db.query(
            AccountVerification.attempt_count,
            func.count(AccountVerification.id).label('count')
        ).group_by(AccountVerification.attempt_count).all()
        
        # Time to completion
        completed_verifications = db.query(
            func.avg(
                func.julianday(AccountVerification.updated_at) - 
                func.julianday(AccountVerification.created_at)
            ).label('avg_days')
        ).filter(
            AccountVerification.status.in_(['completed', 'failed']),
            AccountVerification.updated_at.isnot(None)
        ).scalar() or 0
        
        return {
            "call_duration": {
                "by_outcome": [
                    {
                        "outcome": outcome.value if outcome else "unknown",
                        "avg_duration_seconds": round(avg, 2),
                        "count": count
                    }
                    for outcome, avg, count in duration_by_outcome
                ]
            },
            "retry_distribution": [
                {
                    "attempts": attempts,
                    "count": count
                }
                for attempts, count in retry_stats
            ],
            "time_to_completion": {
                "avg_days": round(completed_verifications, 2),
                "avg_hours": round(completed_verifications * 24, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company-stats")
async def get_company_statistics(db: Session = Depends(get_db)):
    """
    Get statistics grouped by company.
    """
    try:
        from models import AccountVerification
        
        stats = db.query(
            AccountVerification.company_name,
            func.count(AccountVerification.id).label('total'),
            func.sum(case((AccountVerification.account_exists == True, 1), else_=0)).label('verified'),
            func.sum(case((AccountVerification.account_exists == False, 1), else_=0)).label('not_found'),
            func.avg(AccountVerification.attempt_count).label('avg_attempts')
        ).group_by(AccountVerification.company_name).all()
        
        return {
            "companies": [
                {
                    "company": company,
                    "total_verifications": total,
                    "accounts_verified": verified,
                    "accounts_not_found": not_found,
                    "avg_attempts": round(avg_attempts, 2),
                    "success_rate": round((verified / total * 100) if total > 0 else 0, 2)
                }
                for company, total, verified, not_found, avg_attempts in stats
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting company stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
