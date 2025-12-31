"""
Authentication middleware to protect routes.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication on protected routes."""
    
    # Public routes that don't require authentication
    PUBLIC_ROUTES = {
        "/login",
        "/api/auth/login",
        "/api/auth/logout",
        "/static",
        "/health",
        "/favicon.ico"
    }
    
    async def dispatch(self, request: Request, call_next):
        """Check authentication before processing request."""
        
        # Check if route is public
        path = request.url.path
        
        # Allow public routes
        if any(path.startswith(route) for route in self.PUBLIC_ROUTES):
            return await call_next(request)
        
        # Check for session token
        session_token = request.cookies.get("session_token")
        
        if not session_token:
            # For API calls, return 401
            if path.startswith("/api/"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            # For web pages, redirect to login
            return RedirectResponse(url="/login", status_code=302)
        
        # Validate session token
        from api.auth import get_session
        session = get_session(session_token)
        
        if not session:
            logger.warning(f"Invalid or expired session token for path: {path}")
            # For API calls, return 401
            if path.startswith("/api/"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired or invalid"
                )
            # For web pages, redirect to login
            return RedirectResponse(url="/login", status_code=302)
        
        return await call_next(request)
