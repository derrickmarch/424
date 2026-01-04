"""
User management API endpoints (admin-only).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from database import get_db
from models import User, AuditLog
from api.auth import get_current_user, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    new_password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: str
    last_login_at: Optional[str]

    class Config:
        from_attributes = True


def ensure_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


class PaginatedUsers(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=PaginatedUsers)
async def list_users(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_admin(current_user)
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)) | (User.full_name.ilike(like)))
    total = query.count()
    items = query.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedUsers(items=items, total=total, page=page, page_size=page_size)


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_admin(current_user)
    # Unique constraints
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        email=payload.email,
        full_name=payload.full_name,
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action="create",
        resource_type="user",
        resource_id=str(user.id),
        details={"created_username": user.username, "ip": request.client.host if request and request.client else None}
    ))
    db.commit()
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion lockout: ensure at least one admin remains
    if payload.is_admin is not None and user.is_admin and not payload.is_admin:
        # Check if there is at least one other admin
        other_admin = db.query(User).filter(User.id != user.id, User.is_admin == True, User.is_active == True).first()
        if not other_admin:
            raise HTTPException(status_code=400, detail="At least one active admin must remain")

    if payload.email is not None:
        if payload.email == "":
            user.email = None
        else:
            # unique email check
            existing_email = db.query(User).filter(User.email == payload.email, User.id != user.id).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = payload.email

    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.is_admin is not None:
        user.is_admin = payload.is_admin

    if payload.is_active is not None:
        # Prevent deactivating the last active admin
        if user.is_admin and payload.is_active is False:
            other_admin = db.query(User).filter(User.id != user.id, User.is_admin == True, User.is_active == True).first()
            if not other_admin:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last active admin")
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    # Audit log
    changes = {}
    for key in ["email", "full_name", "is_admin", "is_active"]:
        changes[key] = {"from": original.get(key), "to": getattr(user, key)}
    db.add(AuditLog(
        user_id=current_user.id,
        action="update",
        resource_type="user",
        resource_id=str(user.id),
        details={"changes": changes, "ip": request.client.host if request and request.client else None}
    ))
    db.commit()
    return user


@router.post("/{user_id}/reset_password")
async def reset_password(user_id: int, payload: PasswordReset, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    # Audit log (do not include password)
    db.add(AuditLog(
        user_id=current_user.id,
        action="update",
        resource_type="user",
        resource_id=str(user.id),
        details={"password_reset": True, "ip": request.client.host if request and request.client else None}
    ))
    db.commit()
    return {"success": True}


@router.delete("/{user_id}")
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Prefer soft-delete: deactivate instead of delete
    if user.is_active:
        # Prevent deleting/deactivating last admin via delete
        if user.is_admin:
            other_admin = db.query(User).filter(User.id != user.id, User.is_admin == True, User.is_active == True).first()
            if not other_admin:
                raise HTTPException(status_code=400, detail="Cannot delete the last active admin")
        user.is_active = False
        db.commit()
        # Audit log
        db.add(AuditLog(
            user_id=current_user.id,
            action="update",
            resource_type="user",
            resource_id=str(user.id),
            details={"deactivated": True, "ip": request.client.host if request and request.client else None}
        ))
        db.commit()
        return {"success": True, "message": "User deactivated"}
    else:
        db.delete(user)
        db.commit()
        # Audit log
        db.add(AuditLog(
            user_id=current_user.id,
            action="delete",
            resource_type="user",
            resource_id=str(user_id),
            details={"deleted": True, "ip": request.client.host if request and request.client else None}
        ))
        db.commit()
        return {"success": True, "message": "User deleted"}
