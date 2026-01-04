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
import re
from urllib.parse import urlparse

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
        # Telephony Provider
        {
            "key": "telephony_provider",
            "value": (app_settings.telephony_provider or "twilio"),
            "type": "string",
            "description": "Active telephony provider (twilio, vonage, or bland)",
            "sensitive": False
        },
        # Test mode verified phone number (used for trial compliance)
        {
            "key": "test_phone_number",
            "value": app_settings.test_phone_number,
            "type": "string",
            "description": "Verified phone number to call in TEST MODE (Twilio trial restriction)",
            "sensitive": False
        },
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
       # Vonage credentials
       {
           "key": "vonage_api_key",
           "value": "",
           "type": "string",
           "description": "Vonage API Key",
           "sensitive": True
       },
       {
           "key": "vonage_api_secret",
           "value": "",
           "type": "string",
           "description": "Vonage API Secret",
           "sensitive": True
       },
       {
           "key": "vonage_from_number",
           "value": "",
           "type": "string",
           "description": "Vonage virtual number to place calls from",
           "sensitive": False
       },
       # Bland credentials and config
       {
           "key": "bland_api_key",
           "value": app_settings.bland_api_key,
           "type": "string",
           "description": "Bland API Key",
           "sensitive": True
       },
       {
           "key": "bland_project_id",
           "value": app_settings.bland_project_id,
           "type": "string",
           "description": "Bland Project/Agent ID (optional)",
           "sensitive": False
       },
       {
           "key": "bland_from_number",
           "value": app_settings.bland_from_number,
           "type": "string",
           "description": "Bland verified caller ID (E.164)",
           "sensitive": False
       },
       {
           "key": "bland_webhook_base_url",
           "value": app_settings.bland_webhook_base_url or app_settings.twilio_webhook_base_url,
           "type": "string",
           "description": "Public base URL for Bland webhooks (defaults to Twilio base if empty)",
           "sensitive": False
       },
       # Telnyx
       {"key": "telnyx_api_key", "value": app_settings.telnyx_api_key, "type": "string", "description": "Telnyx API Key", "sensitive": True},
       {"key": "telnyx_from_number", "value": app_settings.telnyx_from_number, "type": "string", "description": "Telnyx From Number", "sensitive": False},
       {"key": "telnyx_webhook_base_url", "value": app_settings.telnyx_webhook_base_url or app_settings.twilio_webhook_base_url, "type": "string", "description": "Telnyx Webhook Base URL", "sensitive": False},
       # Plivo
       {"key": "plivo_auth_id", "value": app_settings.plivo_auth_id, "type": "string", "description": "Plivo Auth ID", "sensitive": True},
       {"key": "plivo_auth_token", "value": app_settings.plivo_auth_token, "type": "string", "description": "Plivo Auth Token", "sensitive": True},
       {"key": "plivo_from_number", "value": app_settings.plivo_from_number, "type": "string", "description": "Plivo From Number", "sensitive": False},
       {"key": "plivo_webhook_base_url", "value": app_settings.plivo_webhook_base_url or app_settings.twilio_webhook_base_url, "type": "string", "description": "Plivo Webhook Base URL", "sensitive": False},
       # SignalWire
       {"key": "signalwire_project", "value": app_settings.signalwire_project, "type": "string", "description": "SignalWire Project", "sensitive": True},
       {"key": "signalwire_token", "value": app_settings.signalwire_token, "type": "string", "description": "SignalWire Token", "sensitive": True},
       {"key": "signalwire_from_number", "value": app_settings.signalwire_from_number, "type": "string", "description": "SignalWire From Number", "sensitive": False},
       {"key": "signalwire_webhook_base_url", "value": app_settings.signalwire_webhook_base_url or app_settings.twilio_webhook_base_url, "type": "string", "description": "SignalWire Webhook Base URL", "sensitive": False},
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
       {
           "key": "twilio_webhook_base_url",
           "value": app_settings.twilio_webhook_base_url,
           "type": "string",
           "description": "Public base URL for Twilio webhooks (e.g., https://your-domain.com)",
           "sensitive": False
       },
       {
           "key": "vonage_webhook_base_url",
           "value": "",
           "type": "string",
           "description": "Public base URL for Vonage webhooks (optional; defaults to Twilio base if empty)",
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
    Checks runtime override from database first, then environment variable.
    """
    from config import settings
    import os
    
    # Get actual runtime mode (includes database override)
    test_mode = settings.get_test_mode()
    
    # Check platform
    is_render = os.getenv('RENDER') == 'true'
    platform = "Render.com" if is_render else "Local"
    
    return {
        "test_mode": test_mode,
        "mode_name": "TEST MODE 🧪" if test_mode else "LIVE MODE 📞",
        "platform": platform,
        "env_test_mode": settings.test_mode,  # Original env var value
        "using_override": test_mode != settings.test_mode,  # True if database override is active
        "test_phone_number": settings.test_phone_number
    }


@router.post("/mode/toggle")
async def toggle_mode(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Toggle between test mode and live mode.
    
    IMPORTANT: This endpoint works differently based on environment:
    - LOCAL: Modifies .env file (restart required)
    - RENDER/CLOUD: Uses database runtime settings (no restart required)
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from config import settings
    import os
    from pathlib import Path
    
    current_mode = settings.test_mode
    new_mode = not current_mode
    mode_name = "TEST MODE 🧪" if new_mode else "LIVE MODE 📞"
    
    # Check if running on Render or in production
    is_render = os.getenv('RENDER') == 'true'
    is_production = os.getenv('APP_ENV', 'development') == 'production'
    
    if is_render or is_production:
        # On Render/Cloud: Use database runtime settings (hot-reload without restart)
        logger.info(f"Running on cloud platform. Using database runtime settings for mode toggle.")
        
        # Store the mode in database
        set_setting(
            db=db,
            key="test_mode_override",
            value=str(new_mode).lower(),
            description="Runtime test mode override (takes precedence over env var)",
            setting_type="bool",
            is_sensitive=False,
            username=user.username
        )
        
        # Force reload settings by clearing any cached instances
        # Re-initialization note: provider facade reads mode dynamically; no explicit reset needed
        logger.info("Mode toggled; provider services will reflect new mode on next use.")
        
        logger.info(f"Mode toggled to {mode_name} by {user.username} using database runtime settings.")
        
        return {
            "success": True,
            "message": f"Mode changed to {mode_name}. ✅ Changes applied immediately (no restart required). Note: To make permanent, update TEST_MODE environment variable in Render dashboard.",
            "new_mode": new_mode,
            "restart_required": False,
            "mode_name": mode_name,
            "platform": "cloud",
            "note": "Using runtime database settings. For permanent changes, update environment variables in Render.com dashboard."
        }
    
    # Development/Local mode - try to modify .env file
    env_path = Path(".env")
    if not env_path.exists():
        # .env doesn't exist (common on Render)
        # Fall back to database runtime settings
        logger.warning(".env file not found. Using database runtime settings instead.")
        
        set_setting(
            db=db,
            key="test_mode_override",
            value=str(new_mode).lower(),
            description="Runtime test mode override (takes precedence over env var)",
            setting_type="bool",
            is_sensitive=False,
            username=user.username
        )
        
        return {
            "success": True,
            "message": f"Mode changed to {mode_name}. ✅ Using runtime settings (no restart required).",
            "new_mode": new_mode,
            "restart_required": False,
            "mode_name": mode_name,
            "platform": "database",
            "note": ".env file not found. Using database runtime settings instead."
        }
    
    # Local development with .env file
    try:
        env_content = env_path.read_text(encoding='utf-8')
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
            new_lines.append(f'TEST_MODE={str(new_mode).lower()}')
        
        # Write back to .env
        env_path.write_text('\n'.join(new_lines), encoding='utf-8')
        
        logger.info(f"Mode toggled to {mode_name} by {user.username}. .env file updated. Restart required.")
        
        return {
            "success": True,
            "message": f"Mode changed to {mode_name}. ⚠️ Please restart the application for changes to take effect.",
            "new_mode": new_mode,
            "restart_required": True,
            "mode_name": mode_name,
            "platform": "local"
        }
    except Exception as e:
        logger.error(f"Failed to modify .env file: {e}. Falling back to database runtime settings.", exc_info=True)
        
        # Fallback to database runtime settings
        set_setting(
            db=db,
            key="test_mode_override",
            value=str(new_mode).lower(),
            description="Runtime test mode override (takes precedence over env var)",
            setting_type="bool",
            is_sensitive=False,
            username=user.username
        )
        
        return {
            "success": True,
            "message": f"Mode changed to {mode_name}. ✅ Using runtime settings (no restart required).",
            "new_mode": new_mode,
            "restart_required": False,
            "mode_name": mode_name,
            "platform": "database",
            "note": f"Could not modify .env file: {str(e)}. Using database runtime settings instead."
        }


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
    
    # Server-side validation for certain keys
    if key == "telephony_provider":
        allowed = {"twilio", "vonage", "bland"}
        if update.setting_value.lower() not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid provider. Allowed: {', '.join(sorted(allowed))}")

    setting = set_setting(
        db=db,
        key=key,
        value=update.setting_value,
        description=update.description,
        username=user.username
    )
    
    # Mask sensitive values in logs to avoid leaking secrets
    masked_value = update.setting_value
    if key in {"openai_api_key", "twilio_auth_token", "vonage_api_secret", "bland_api_key", "telnyx_api_key", "plivo_auth_id", "plivo_auth_token", "signalwire_project", "signalwire_token"}:
        if isinstance(masked_value, str) and len(masked_value) > 8:
            masked_value = masked_value[:4] + "****" + masked_value[-4:]
        else:
            masked_value = "****"
    logger.info(f"Setting '{key}' updated by {user.username} to: {masked_value}")
    
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
