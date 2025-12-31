"""
Settings management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import SystemSettings, User
from api.auth import get_current_user
from typing import Optional, List
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    setting_key: str
    setting_value: str
    description: Optional[str] = None


class SettingResponse(BaseModel):
    setting_key: str
    setting_value: str
    setting_type: str
    description: Optional[str]
    is_sensitive: bool
    updated_at: str


def get_setting(db: Session, key: str, default: str = None) -> Optional[str]:
    """Get a setting value from database."""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    return setting.setting_value if setting else default


def set_setting(db: Session, key: str, value: str, description: str = None, 
                setting_type: str = "string", is_sensitive: bool = False,
                username: str = None):
    """Set or update a setting in database."""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    
    if setting:
        setting.setting_value = value
        if description:
            setting.description = description
        setting.updated_by = username
    else:
        setting = SystemSettings(
            setting_key=key,
            setting_value=value,
            setting_type=setting_type,
            description=description,
            is_sensitive=is_sensitive,
            updated_by=username
        )
        db.add(setting)
    
    db.commit()
    return setting


def init_default_settings(db: Session):
    """Initialize default settings if they don't exist."""
    from config import settings as app_settings
    
    defaults = [
        # API Keys (sensitive)
        {
            "key": "twilio_account_sid",
            "value": app_settings.twilio_account_sid,
            "type": "string",
            "description": "Twilio Account SID for making phone calls",
            "sensitive": True
        },
        {
            "key": "twilio_auth_token",
            "value": app_settings.twilio_auth_token,
            "type": "string",
            "description": "Twilio Auth Token for API authentication",
            "sensitive": True
        },
        {
            "key": "twilio_phone_number",
            "value": app_settings.twilio_phone_number,
            "type": "string",
            "description": "Twilio phone number to make calls from (e.g., +1234567890)",
            "sensitive": False
        },
        {
            "key": "openai_api_key",
            "value": app_settings.openai_api_key,
            "type": "string",
            "description": "OpenAI API Key for AI agent conversations",
            "sensitive": True
        },
        {
            "key": "openai_model",
            "value": app_settings.openai_model,
            "type": "string",
            "description": "OpenAI model to use (e.g., gpt-4-turbo-preview, gpt-3.5-turbo)",
            "sensitive": False
        },
        # Call Configuration
        {
            "key": "citibank_phone_number",
            "value": "+18005742847",  # Citibank customer service
            "type": "string",
            "description": "Citibank phone number to call for verification",
            "sensitive": False
        },
        {
            "key": "accounts_per_call",
            "value": "2",
            "type": "int",
            "description": "Number of accounts to verify per call (1-2 recommended)",
            "sensitive": False
        },
        {
            "key": "call_timeout_seconds",
            "value": str(app_settings.call_timeout_seconds),
            "type": "int",
            "description": "Maximum call duration in seconds",
            "sensitive": False
        },
        {
            "key": "max_concurrent_calls",
            "value": str(app_settings.max_concurrent_calls),
            "type": "int",
            "description": "Maximum number of concurrent calls",
            "sensitive": False
        },
        # Scheduler Configuration
        {
            "key": "enable_auto_calling",
            "value": str(app_settings.enable_auto_calling).lower(),
            "type": "bool",
            "description": "Enable automatic batch calling",
            "sensitive": False
        },
        {
            "key": "call_loop_interval_minutes",
            "value": str(app_settings.call_loop_interval_minutes),
            "type": "int",
            "description": "Minutes between auto-calling batches",
            "sensitive": False
        },
        {
            "key": "batch_size_per_loop",
            "value": str(app_settings.batch_size_per_loop),
            "type": "int",
            "description": "Number of records to process per batch",
            "sensitive": False
        },
        # Retry Configuration
        {
            "key": "max_retry_attempts",
            "value": str(app_settings.max_retry_attempts),
            "type": "int",
            "description": "Maximum number of retry attempts for failed calls",
            "sensitive": False
        }
    ]
    
    for setting_data in defaults:
        existing = db.query(SystemSettings).filter(
            SystemSettings.setting_key == setting_data["key"]
        ).first()
        
        if not existing:
            setting = SystemSettings(
                setting_key=setting_data["key"],
                setting_value=setting_data["value"],
                setting_type=setting_data["type"],
                description=setting_data["description"],
                is_sensitive=setting_data["sensitive"]
            )
            db.add(setting)
    
    db.commit()
    logger.info("Initialized default settings")


@router.get("/mode")
async def get_mode(user: User = Depends(get_current_user)):
    """
    Get current system mode (test/live).
    """
    from config import settings
    return {
        "test_mode": settings.test_mode,
        "mode_name": "TEST MODE 🧪" if settings.test_mode else "LIVE MODE 📞"
    }


@router.post("/mode/toggle")
async def toggle_mode(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Toggle between test mode and live mode.
    Note: On cloud platforms like Render, environment variables should be changed
    through the platform's dashboard, not by modifying files.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from config import settings
    import os
    from pathlib import Path
    
    # Check if running in production/cloud environment
    app_env = os.getenv('APP_ENV', 'development')
    
    if app_env == 'production':
        # In production (Render/cloud), don't modify .env file
        current_mode = "TEST MODE 🧪" if settings.test_mode else "LIVE MODE 📞"
        return {
            "success": False,
            "message": f"Current mode: {current_mode}. In production, please change TEST_MODE environment variable in your hosting platform's dashboard (e.g., Render.com Environment tab), then restart the service.",
            "current_mode": settings.test_mode,
            "restart_required": False,
            "production_note": "Environment variables must be changed through hosting platform dashboard"
        }
    
    # Development mode - allow file modification
    env_path = Path(".env")
    if not env_path.exists():
        raise HTTPException(status_code=500, detail=".env file not found")
    
    try:
        env_content = env_path.read_text()
        lines = env_content.split('\n')
        
        # Toggle TEST_MODE value
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith('TEST_MODE='):
                found = True
                current_value = line.split('=', 1)[1].strip().lower()
                new_value = 'false' if current_value == 'true' else 'true'
                new_lines.append(f'TEST_MODE={new_value}')
            else:
                new_lines.append(line)
        
        # If TEST_MODE wasn't in .env, add it
        if not found:
            new_lines.append('TEST_MODE=true')
        
        # Write back to .env
        env_path.write_text('\n'.join(new_lines))
        
        new_mode = not settings.test_mode
        mode_name = "TEST MODE 🧪" if new_mode else "LIVE MODE 📞"
        
        logger.info(f"Mode toggled by {user.username}. New mode: {mode_name}. Restart required.")
        
        return {
            "success": True,
            "message": f"Mode changed to {mode_name}. Please restart the application for changes to take effect.",
            "new_mode": new_mode,
            "restart_required": True
        }
    except Exception as e:
        logger.error(f"Failed to toggle mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to modify .env file: {str(e)}")


@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get all system settings (non-sensitive only for non-admins).
    """
    # Initialize defaults if needed
    init_default_settings(db)
    
    query = db.query(SystemSettings)
    
    # Non-admin users can't see sensitive settings
    if not user.is_admin:
        query = query.filter(SystemSettings.is_sensitive == False)
    
    settings = query.all()
    
    return [
        SettingResponse(
            setting_key=s.setting_key,
            setting_value=s.setting_value if not s.is_sensitive or user.is_admin else "••••••••",
            setting_type=s.setting_type,
            description=s.description,
            is_sensitive=s.is_sensitive,
            updated_at=s.updated_at.isoformat()
        )
        for s in settings
    ]


@router.get("/{key}")
async def get_setting_by_key(
    key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get a specific setting by key.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    if setting.is_sensitive and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied to sensitive setting")
    
    return {
        "setting_key": setting.setting_key,
        "setting_value": setting.setting_value,
        "setting_type": setting.setting_type,
        "description": setting.description,
        "is_sensitive": setting.is_sensitive,
        "updated_at": setting.updated_at.isoformat(),
        "updated_by": setting.updated_by
    }


@router.put("/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update a setting value.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    setting = set_setting(
        db=db,
        key=key,
        value=update.setting_value,
        description=update.description,
        username=user.username
    )
    
    logger.info(f"Setting '{key}' updated by {user.username} to: {update.setting_value}")
    
    return {
        "success": True,
        "message": f"Setting '{key}' updated successfully",
        "setting": {
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "updated_at": setting.updated_at.isoformat()
        }
    }


@router.post("/")
async def create_setting(
    setting_data: SettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a new setting.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if setting already exists
    existing = db.query(SystemSettings).filter(
        SystemSettings.setting_key == setting_data.setting_key
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Setting already exists. Use PUT to update.")
    
    setting = set_setting(
        db=db,
        key=setting_data.setting_key,
        value=setting_data.setting_value,
        description=setting_data.description,
        username=user.username
    )
    
    return {
        "success": True,
        "message": "Setting created successfully",
        "setting": {
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "updated_at": setting.updated_at.isoformat()
        }
    }
