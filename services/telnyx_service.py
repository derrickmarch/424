from typing import Optional, Dict, Any
import logging, time, random
import httpx
from sqlalchemy.orm import Session
from config import settings as env_settings
from services.settings_service import get_runtime_settings

logger = logging.getLogger(__name__)

class TelnyxService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        runtime = get_runtime_settings(db) if db else None
        self.api_key: str = (runtime.get("telnyx_api_key") if runtime else None) or getattr(env_settings, "telnyx_api_key", "")
        self.from_number: str = (runtime.get("telnyx_from_number") if runtime else None) or getattr(env_settings, "telnyx_from_number", "")
        self.webhook_base: str = (runtime.get("telnyx_webhook_base_url") if runtime else None) or getattr(env_settings, "telnyx_webhook_base_url", getattr(env_settings, "twilio_webhook_base_url", ""))
        self._mock = not self.api_key

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        if self._mock:
            call_id = f"telnyx-mock-{verification_id}-{int(time.time())}-{random.randint(1000,9999)}"
            logger.info(f"[MOCK] Telnyx call {call_id} to {to_number}")
            # Simulate webhook
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
        # Real call placeholder (to be implemented with Telnyx Calls API)
        logger.warning("Telnyx live call not yet implemented; falling back to mock")
        return self.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)

    def hangup_call(self, call_id: str) -> bool:
        logger.info(f"Telnyx hangup {call_id} (mock)")
        return True

    def get_account_balance(self) -> Dict[str, Any]:
        return {"provider": "telnyx", "balance": None}

    def get_from_number(self) -> Optional[str]:
        return self.from_number or None
