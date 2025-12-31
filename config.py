"""
Configuration management for the Account Verifier system.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite:///./account_verifier.db"
    
    # Twilio - Made optional with defaults for easier testing
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_webhook_base_url: str = ""
    
    # OpenAI - Made optional with default for easier testing
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"  # Must be set in production
    
    # Testing Mode
    test_mode: bool = True  # True = mock calls, False = real calls
    test_phone_number: str = "+19092028031"  # Verified test number for trial accounts
    
    def get_test_mode(self) -> bool:
        """
        Get test mode setting with runtime override support.
        Checks database for runtime override first, then falls back to env var.
        This allows hot-reloading test mode without restarting the app.
        """
        try:
            # Try to get runtime override from database
            from database import get_db
            db = next(get_db())
            from models import SystemSettings
            
            override = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "test_mode_override"
            ).first()
            
            if override and override.setting_value:
                runtime_mode = override.setting_value.lower() in ('true', '1', 'yes')
                return runtime_mode
        except:
            # If database is not available or not initialized yet, use env var
            pass
        
        # Fall back to environment variable
        return self.test_mode
    
    # Call Settings
    max_concurrent_calls: int = 1
    max_retry_attempts: int = 2
    retry_backoff_minutes: str = "15,120"
    call_timeout_seconds: int = 300
    
    # Looping Call Settings
    enable_auto_calling: bool = True
    call_loop_interval_minutes: int = 5
    batch_size_per_loop: int = 10
    
    # Compliance
    enable_call_recording: bool = True
    require_recording_consent: bool = True
    enable_transcription: bool = True
    
    # Notifications
    admin_email: str = ""
    admin_phone: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def retry_backoff_list(self) -> List[int]:
        """Parse retry backoff minutes into a list."""
        return [int(x.strip()) for x in self.retry_backoff_minutes.split(",")]


# Global settings instance
settings = Settings()
