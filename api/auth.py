"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBasic()

# Session storage (in production, use Redis or similar)
active_sessions = {}
SESSION_DURATION = timedelta(hours=24)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class ChangeCredentialsRequest(BaseModel):
    current_password: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def create_session(username: str) -> str:
    """Create a new session token."""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        'username': username,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + SESSION_DURATION
    }
    return token


def get_session(token: str) -> Optional[dict]:
    """Get session data if valid."""
    logger.debug(f"Checking session token: {token[:20]}... (Total active sessions: {len(active_sessions)})")
    session = active_sessions.get(token)
    if session and session['expires_at'] > datetime.utcnow():
        logger.debug(f"Valid session found for user: {session['username']}")
        return session
    elif session:
        # Expired session
        logger.info(f"Session expired for token: {token[:20]}...")
        del active_sessions[token]
    else:
        logger.warning(f"Session not found for token: {token[:20]}...")
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get the current authenticated user from session."""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    session = get_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
    
    user = db.query(User).filter(User.username == session['username']).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


def create_default_admin(db: Session):
    """Create default admin user if no users exist."""
    user_count = db.query(User).count()
    if user_count == 0:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            email="admin@example.com",
            full_name="Administrator",
            is_admin=True,
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info("Created default admin user")


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and create session.
    """
    # Ensure default admin exists
    create_default_admin(db)
    
    # Find user
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create session
    token = create_session(user.username)
    
    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=int(SESSION_DURATION.total_seconds()),
        samesite="lax",
        path="/"
    )
    
    logger.info(f"Session created for user {user.username} with token: {token[:20]}...")
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User {user.username} logged in")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        user={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    )


@router.post("/change_credentials")
async def change_credentials(
    payload: ChangeCredentialsRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Change the current user's username and/or password. Requires current password.
    """
    token = request.cookies.get('session_token')
    session = get_session(token) if token else None
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = db.query(User).filter(User.username == session['username']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    updates = []
    
    if payload.new_username and payload.new_username != user.username:
        # Ensure username not taken
        existing = db.query(User).filter(User.username == payload.new_username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = payload.new_username
        updates.append('username')
    
    if payload.new_password:
        user.password_hash = hash_password(payload.new_password)
        updates.append('password')
    
    if not updates:
        return {"success": True, "message": "No changes"}
    
    db.commit()
    
    # If username changed, rotate session to avoid mismatch
    if 'username' in updates:
        # invalidate old session and set new one via cookie response in a real request
        # Here we simply update the session store
        active_sessions[token]['username'] = user.username
    
    return {"success": True, "message": "Credentials updated", "updated": updates}


@router.post("/logout")
async def logout(response: Response, request: Request):
    """
    Logout user and destroy session.
    """
    token = request.cookies.get('session_token')
    if token and token in active_sessions:
        del active_sessions[token]
    
    response.delete_cookie("session_token")
    
    return {"success": True, "message": "Logged out"}


@router.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
    }
