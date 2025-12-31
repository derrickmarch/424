"""
Audit logging for all system actions.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])


def log_action(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """
    Log an audit event.
    
    Args:
        db: Database session
        user_id: ID of user performing action
        action: Action performed (create, update, delete, view, etc.)
        resource_type: Type of resource (verification, user, setting, etc.)
        resource_id: ID of the resource
        details: Additional details (JSON)
        ip_address: IP address of request
    """
    from models import AuditLog
    
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_entry)
        db.commit()
        
        logger.info(
            f"📝 Audit log",
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id
        )
    
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        # Don't fail the main operation if audit logging fails
        db.rollback()


@router.get("/logs")
async def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get audit logs with filtering.
    """
    try:
        from models import AuditLog
        
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        total = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                }
                for log in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/{user_id}")
async def get_user_activity(
    user_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get recent activity for a specific user.
    """
    try:
        from models import AuditLog
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= start_date
        ).order_by(AuditLog.timestamp.desc()).limit(100).all()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "activity_count": len(logs),
            "activities": [
                {
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                }
                for log in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
