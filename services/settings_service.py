"""
Service to retrieve runtime settings from database with fallback to environment variables.
This allows settings to be changed through the UI without restarting the application.
"""
from sqlalchemy.orm import Session
from models import SystemSettings
from config import settings as env_settings
import logging

logger = logging.getLogger(__name__)


class RuntimeSettings:
    """
    Runtime settings manager that reads from database first, then falls back to env vars.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}
    
    def get(self, key: str, default=None, setting_type: str = "string"):
        """Get a setting value from database or fallback to environment."""
        # Try database first
        setting = self.db.query(SystemSettings).filter(
            SystemSettings.setting_key == key
        ).first()
        
        if setting:
            value = setting.setting_value
            
            # Convert type
            if setting_type == "int":
                return int(value) if value else default
            elif setting_type == "bool":
                return value.lower() in ('true', '1', 'yes') if value else default
            elif setting_type == "float":
                return float(value) if value else default
            else:
                return value if value else default
        
        # Fallback to environment variable
        return default
    
    def get_twilio_account_sid(self) -> str:
        """Get Twilio Account SID."""
        return self.get("twilio_account_sid", env_settings.twilio_account_sid)
    
    def get_twilio_auth_token(self) -> str:
        """Get Twilio Auth Token."""
        return self.get("twilio_auth_token", env_settings.twilio_auth_token)
    
    def get_twilio_phone_number(self) -> str:
        """Get Twilio Phone Number."""
        return self.get("twilio_phone_number", env_settings.twilio_phone_number)
    
    def get_openai_api_key(self) -> str:
        """Get OpenAI API Key."""
        return self.get("openai_api_key", env_settings.openai_api_key)
    
    def get_openai_model(self) -> str:
        """Get OpenAI Model."""
        return self.get("openai_model", env_settings.openai_model)
    
    def get_max_concurrent_calls(self) -> int:
        """Get max concurrent calls."""
        return self.get("max_concurrent_calls", env_settings.max_concurrent_calls, "int")
    
    def get_call_timeout_seconds(self) -> int:
        """Get call timeout in seconds."""
        return self.get("call_timeout_seconds", env_settings.call_timeout_seconds, "int")
    
    def get_enable_auto_calling(self) -> bool:
        """Get auto calling enabled status."""
        return self.get("enable_auto_calling", env_settings.enable_auto_calling, "bool")
    
    def get_call_loop_interval_minutes(self) -> int:
        """Get call loop interval in minutes."""
        return self.get("call_loop_interval_minutes", env_settings.call_loop_interval_minutes, "int")
    
    def get_batch_size_per_loop(self) -> int:
        """Get batch size per loop."""
        return self.get("batch_size_per_loop", env_settings.batch_size_per_loop, "int")
    
    def get_max_retry_attempts(self) -> int:
        """Get max retry attempts."""
        return self.get("max_retry_attempts", env_settings.max_retry_attempts, "int")
    
    def get_citibank_phone_number(self) -> str:
        """Get Citibank phone number."""
        return self.get("citibank_phone_number", "+18005742847")
    
    def get_accounts_per_call(self) -> int:
        """Get accounts per call."""
        return self.get("accounts_per_call", 2, "int")


def get_runtime_settings(db: Session) -> RuntimeSettings:
    """Get runtime settings instance."""
    return RuntimeSettings(db)
