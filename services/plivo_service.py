from typing import Optional, Dict, Any
import logging, time, random
import httpx
from sqlalchemy.orm import Session
from config import settings as env_settings
from services.settings_service import get_runtime_settings

logger = logging.getLogger(__name__)

class PlivoService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        runtime = get_runtime_settings(db) if db else None
        self.auth_id: str = (runtime.get("plivo_auth_id") if runtime else None) or getattr(env_settings, "plivo_auth_id", "")
        self.auth_token: str = (runtime.get("plivo_auth_token") if runtime else None) or getattr(env_settings, "plivo_auth_token", "")
        self.from_number: str = (runtime.get("plivo_from_number") if runtime else None) or getattr(env_settings, "plivo_from_number", "")
        self.webhook_base: str = (runtime.get("plivo_webhook_base_url") if runtime else None) or getattr(env_settings, "plivo_webhook_base_url", getattr(env_settings, "twilio_webhook_base_url", ""))
        self._mock = not (self.auth_id and self.auth_token)

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        if self._mock:
            call_id = f"plivo-mock-{verification_id}-{int(time.time())}-{random.randint(1000,9999)}"
            logger.info(f"[MOCK] Plivo call {call_id} to {to_number}")
            try:
                import threading
                def _cb():
                    time.sleep(1)
                    payload = {"call_id": call_id, "status": "completed", "metadata": {"verification_id": verification_id}}
                    with httpx.Client(timeout=10) as c:
                        c.post(webhook_url, json=payload)
                threading.Thread(target=_cb, daemon=True).start()
            except Exception:
                pass
            return call_id
        logger.warning("Plivo live call not yet implemented; falling back to mock")
        return self.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)

    def hangup_call(self, call_id: str) -> bool:
        logger.info(f"Plivo hangup {call_id} (mock)")
        return True

    def get_account_balance(self) -> Dict[str, Any]:
        return {"provider": "plivo", "balance": None}

    def get_from_number(self) -> Optional[str]:
        return self.from_number or None
