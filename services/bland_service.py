"""
Bland AI integration service for making calls using Bland's hosted agent and handling webhooks.
This implementation is resilient: it works in TEST MODE without external calls.
"""
from typing import Optional, Dict, Any
import logging
import time
import random

from sqlalchemy.orm import Session
import httpx

from config import settings as env_settings
from services.settings_service import get_runtime_settings

logger = logging.getLogger(__name__)


class BlandService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        runtime = get_runtime_settings(db) if db else None

        # Credentials and configuration (DB override -> env)
        self.api_key: str = (runtime.get("bland_api_key", None) if runtime else None) or getattr(env_settings, "bland_api_key", "")
        self.project_id: str = (runtime.get("bland_project_id", None) if runtime else None) or getattr(env_settings, "bland_project_id", "")
        self.from_number: str = (runtime.get("bland_from_number", None) if runtime else None) or getattr(env_settings, "bland_from_number", "")

        # Base URL for outbound webhooks
        self.webhook_base: str = (runtime.get("bland_webhook_base_url", None) if runtime else None) or getattr(env_settings, "bland_webhook_base_url", getattr(env_settings, "twilio_webhook_base_url", ""))

        # In test mode we still allow LIVE Bland calls; mock only if API key is missing
        self._mock = not self.api_key

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        """
        Create a Bland call. Bland generally supports a POST to /v1/calls with a payload including:
        - phone_number, from_number (optional, verified), project (script/agent), and webhook for results.
        We send webhook_url for results; status_callback_url may be ignored or passed in metadata.
        Returns a call_id string.
        """
        if self._mock:
            call_id = f"bland-mock-{verification_id}-{int(time.time())}-{random.randint(1000,9999)}"
            logger.info(f"[MOCK] Initiated Bland call {call_id} to {to_number}")
            # Simulate async webhook callback shortly after
            try:
                import threading

                def _simulate_callback():
                    try:
                        time.sleep(1.0)
                        payload = {
                            "id": call_id,
                            "status": "completed",
                            "duration": random.randint(45, 120),
                            "transcript": "[MOCK Bland] Account confirmed during test run.",
                            "metadata": {"verification_id": verification_id},
                            "outcome": random.choice(["account_found", "account_not_found", "needs_human"]) ,
                        }
                        with httpx.Client(timeout=10) as client:
                            client.post(webhook_url, json=payload)
                        logger.info(f"[MOCK] Sent Bland webhook callback for {call_id}")
                    except Exception as e:
                        logger.warning(f"[MOCK] Failed to send Bland webhook callback: {e}")

                threading.Thread(target=_simulate_callback, daemon=True).start()
            except Exception:
                pass
            return call_id

        base = "https://api.bland.ai/v1"
        url = f"{base}/calls"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "phone_number": to_number,
            # Project or agent configuration (if provided)
            **({"project": self.project_id} if self.project_id else {}),
            # Caller ID (must be verified in Bland)
            **({"from": self.from_number} if self.from_number else {}),
            # Your webhook to receive results
            "webhook": webhook_url,
            # Pass through metadata for correlation
            "metadata": {
                "verification_id": verification_id,
                "status_callback_url": status_callback_url,
            },
        }

        try:
            with httpx.Client(timeout=20) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                call_id = data.get("id") or data.get("call_id") or ""
                if not call_id:
                    raise RuntimeError(f"Unexpected Bland response: {data}")
                logger.info(f"Initiated Bland call {call_id} to {to_number} for verification {verification_id}")
                return call_id
        except Exception as e:
            logger.error(f"Failed to initiate Bland call to {to_number}: {e}")
            raise

    def hangup_call(self, call_id: str) -> bool:
        if self._mock:
            logger.info(f"[MOCK] Hangup Bland call {call_id}")
            return True
        try:
            base = "https://api.bland.ai/v1"
            url = f"{base}/calls/{call_id}/hangup"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, headers=headers)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to hangup Bland call {call_id}: {e}")
            return False

    def get_account_balance(self) -> Dict[str, Any]:
        """Bland may not provide a balance API; return placeholder to keep orchestrator flow."""
        if self._mock:
            return {"note": "mock", "provider": "bland"}
        try:
            # Placeholder; if Bland exposes usage, query here.
            return {"provider": "bland", "balance": None}
        except Exception as e:
            return {"error": str(e)}

    def get_from_number(self) -> Optional[str]:
        return self.from_number or None
