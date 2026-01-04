"""
Advanced search and filtering API.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from database import get_db
from typing import Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("/verifications")
async def search_verifications(
    # Text search
    q: Optional[str] = Query(None, description="Search query (name, account, phone)"),
    
    # Filters
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    company: Optional[str] = Query(None, description="Filter by company"),
    account_exists: Optional[bool] = Query(None, description="Filter by account exists"),
    priority: Optional[int] = Query(None, description="Filter by priority"),
    
    # Date range
    created_after: Optional[datetime] = Query(None, description="Created after date"),
    created_before: Optional[datetime] = Query(None, description="Created before date"),
    
    # Pagination
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    
    # Sorting
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    
    db: Session = Depends(get_db)
):
    """
    Advanced search with multiple filters and sorting.
    """
    try:
        from models import AccountVerification, VerificationStatus
        
        query = db.query(AccountVerification)
        
        # Text search across multiple fields
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    AccountVerification.customer_name.ilike(search_pattern),
                    AccountVerification.account_number.ilike(search_pattern),
                    AccountVerification.customer_phone.ilike(search_pattern),
                    AccountVerification.company_name.ilike(search_pattern),
                    AccountVerification.verification_id.ilike(search_pattern)
                )
            )
        
        # Status filter
        if status:
            query = query.filter(AccountVerification.status.in_(status))
        
        # Company filter
        if company:
            query = query.filter(AccountVerification.company_name.ilike(f"%{company}%"))
        
        # Account exists filter
        if account_exists is not None:
            query = query.filter(AccountVerification.account_exists == account_exists)
        
        # Priority filter
        if priority is not None:
            query = query.filter(AccountVerification.priority == priority)
        
        # Date range filters
        if created_after:
            query = query.filter(AccountVerification.created_at >= created_after)
        
        if created_before:
            query = query.filter(AccountVerification.created_at <= created_before)
        
        # Count total before pagination
        total = query.count()
        
        # Sorting
        if hasattr(AccountVerification, sort_by):
            sort_column = getattr(AccountVerification, sort_by)
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        # Pagination
        verifications = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": [
                {
                    "id": v.verification_id,
                    "verification_id": v.verification_id,
                    "customer_name": v.customer_name,
                    "account_number": v.account_number,
                    "phone_number": v.customer_phone,
                    "company_name": v.company_name,
                    "status": v.status.value if v.status else None,
                    "account_exists": v.account_exists,
                    "priority": v.priority,
                    "attempt_count": v.attempt_count,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "updated_at": v.updated_at.isoformat() if v.updated_at else None
                }
                for v in verifications
            ]
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/options")
async def get_filter_options(db: Session = Depends(get_db)):
    """
    Get available filter options (companies, statuses, etc.).
    """
    try:
        from models import AccountVerification, VerificationStatus
        from sqlalchemy import distinct
        
        # Get unique companies
        companies = db.query(distinct(AccountVerification.company_name)).filter(
            AccountVerification.company_name.isnot(None)
        ).all()
        
        # Get unique priorities
        priorities = db.query(distinct(AccountVerification.priority)).filter(
            AccountVerification.priority.isnot(None)
        ).order_by(AccountVerification.priority).all()
        
        # Get status counts
        status_counts = db.query(
            AccountVerification.status,
            func.count(AccountVerification.verification_id)
        ).group_by(AccountVerification.status).all()
        
        return {
            "companies": [c[0] for c in companies if c[0]],
            "priorities": [p[0] for p in priorities if p[0] is not None],
            "statuses": [
                {
                    "value": status.value if status else "unknown",
                    "count": count
                }
                for status, count in status_counts
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting filter options: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest")
async def search_suggest(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get search suggestions as user types.
    """
    try:
        from models import AccountVerification
        
        search_pattern = f"%{query}%"
        
        # Search in multiple fields
        suggestions = db.query(
            AccountVerification.customer_name,
            AccountVerification.account_number,
            AccountVerification.verification_id
        ).filter(
            or_(
                AccountVerification.customer_name.ilike(search_pattern),
                AccountVerification.account_number.ilike(search_pattern),
                AccountVerification.verification_id.ilike(search_pattern)
            )
        ).limit(limit).all()
        
        results = []
        seen = set()
        
        for name, account, verification_id in suggestions:
            if name and name not in seen:
                results.append({"type": "customer", "value": name})
                seen.add(name)
            if account and account not in seen:
                results.append({"type": "account", "value": account})
                seen.add(account)
            if verification_id and verification_id not in seen:
                results.append({"type": "verification_id", "value": verification_id})
                seen.add(verification_id)
        
        return {
            "query": query,
            "suggestions": results[:limit]
        }
    
    except Exception as e:
        logger.error(f"Search suggest error: {e}")
        return {"query": query, "suggestions": []}
