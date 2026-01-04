"""
Provider-agnostic telephony facade.
"""
from typing import Optional, Literal, Dict, Any
from sqlalchemy.orm import Session
from services.settings_service import get_runtime_settings
from config import settings as env_settings
import logging

logger = logging.getLogger(__name__)

ProviderName = Literal["twilio", "vonage", "bland", "telnyx", "plivo", "signalwire"]


class TelephonyProvider:
    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        raise NotImplementedError

    def hangup_call(self, call_id: str) -> bool:
        raise NotImplementedError

    def get_account_balance(self) -> Dict[str, Any]:
        return {}

    def get_from_number(self) -> Optional[str]:
        return None


class TwilioProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from services.twilio_service import TwilioService
        self._svc = TwilioService(db)

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        return self._svc.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)

    def hangup_call(self, call_id: str) -> bool:
        return self._svc.hangup_call(call_id)

    def get_account_balance(self) -> Dict[str, Any]:
        try:
            return self._svc.get_account_balance()
        except Exception as e:
            logger.warning(f"Twilio balance check failed: {e}")
            return {"error": str(e)}

    def get_from_number(self) -> Optional[str]:
        return self._svc.from_number


class VonageProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from config import settings as env_settings
        self.db = db
        runtime = get_runtime_settings(db) if db else None
        self.api_key = runtime.get("vonage_api_key", "") if runtime else ""
        self.api_secret = runtime.get("vonage_api_secret", "") if runtime else ""
        self.from_number = runtime.get("vonage_from_number", "") if runtime else ""
        
        # Test mode: use mock behavior without SDK
        if env_settings.get_test_mode():
            self._mock = True
            self._calls: Dict[str, Dict[str, Any]] = {}
            return
        
        # Live mode: require SDK
        try:
            import vonage  # type: ignore
        except Exception:
            logger.error("Vonage SDK not installed. Please add 'vonage' to requirements.txt")
            raise
        self._mock = False
        self.vonage = vonage
        # Initialize client (Key/Secret sufficient for Voice create_call)
        self.client = vonage.Client(key=self.api_key, secret=self.api_secret)
        self.voice = vonage.Voice(self.client)

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        if getattr(self, "_mock", False):
            call_id = f"vonage-mock-{verification_id}"
            self._calls[call_id] = {"to": to_number, "status": "started"}
            logger.info(f"[MOCK] Initiated Vonage call {call_id} to {to_number}")
            return call_id
        # For Vonage, webhook_url acts as answer_url, and status_callback_url as event_url
        payload = {
            "to": [{"type": "phone", "number": to_number}],
            "from": {"type": "phone", "number": self.from_number},
            "answer_url": [webhook_url],
            "event_url": [status_callback_url],
        }
        try:
            resp = self.voice.create_call(payload)
            call_id = resp.get("uuid") or resp.get("request_uuid") or ""
            if not call_id:
                raise RuntimeError(f"Unexpected Vonage response: {resp}")
            logger.info(f"Initiated Vonage call {call_id} to {to_number} for verification {verification_id}")
            return call_id
        except Exception as e:
            logger.error(f"Failed to initiate Vonage call to {to_number}: {e}")
            raise

    def hangup_call(self, call_id: str) -> bool:
        if getattr(self, "_mock", False):
            if call_id in self._calls:
                self._calls[call_id]["status"] = "completed"
            return True
        try:
            self.voice.update_call(call_id, action="hangup")
            return True
        except Exception as e:
            logger.error(f"Failed to hangup Vonage call {call_id}: {e}")
            return False

    def get_account_balance(self) -> Dict[str, Any]:
        if getattr(self, "_mock", False):
            return {"balance": "0", "currency": "USD", "note": "mock"}
        try:
            acct = self.client.account.get_balance()
            return {"balance": str(acct.get("value")), "currency": "EUR"}
        except Exception as e:
            return {"error": str(e)}

    def get_from_number(self) -> Optional[str]:
        return self.from_number


class BlandProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from services.bland_service import BlandService
        self._svc = BlandService(db)

    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        return self._svc.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)

    def hangup_call(self, call_id: str) -> bool:
        return self._svc.hangup_call(call_id)

    def get_account_balance(self) -> Dict[str, Any]:
        try:
            return self._svc.get_account_balance()
        except Exception as e:
            logger.warning(f"Bland balance check failed: {e}")
            return {"error": str(e)}

    def get_from_number(self) -> Optional[str]:
        return self._svc.get_from_number()


class TelnyxProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from services.telnyx_service import TelnyxService
        self._svc = TelnyxService(db)
    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        return self._svc.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)
    def hangup_call(self, call_id: str) -> bool:
        return self._svc.hangup_call(call_id)
    def get_account_balance(self) -> Dict[str, Any]:
        return self._svc.get_account_balance()
    def get_from_number(self) -> Optional[str]:
        return self._svc.get_from_number()

class PlivoProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from services.plivo_service import PlivoService
        self._svc = PlivoService(db)
    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        return self._svc.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)
    def hangup_call(self, call_id: str) -> bool:
        return self._svc.hangup_call(call_id)
    def get_account_balance(self) -> Dict[str, Any]:
        return self._svc.get_account_balance()
    def get_from_number(self) -> Optional[str]:
        return self._svc.get_from_number()

class SignalWireProvider(TelephonyProvider):
    def __init__(self, db: Optional[Session] = None):
        from services.signalwire_service import SignalWireService
        self._svc = SignalWireService(db)
    def make_outbound_call(self, to_number: str, verification_id: str, webhook_url: str, status_callback_url: str) -> str:
        return self._svc.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)
    def hangup_call(self, call_id: str) -> bool:
        return self._svc.hangup_call(call_id)
    def get_account_balance(self) -> Dict[str, Any]:
        return self._svc.get_account_balance()
    def get_from_number(self) -> Optional[str]:
        return self._svc.get_from_number()

_telephony_singleton: Optional[TelephonyProvider] = None


def get_telephony_service(db: Optional[Session] = None) -> TelephonyProvider:
    global _telephony_singleton
    # Decide provider from DB runtime setting or env
    provider: ProviderName = "twilio"
    try:
        runtime = get_runtime_settings(db) if db else None
        # DB setting first, else env var, else default
        provider_key = None
        if runtime:
            provider_key = runtime.get("telephony_provider", None)
        if not provider_key:
            provider_key = getattr(env_settings, "telephony_provider", None)
        if not provider_key:
            provider_key = "twilio"
        key = (provider_key or "twilio").lower()
        provider = "bland" if key == "bland" else ("vonage" if key == "vonage" else "twilio")
    except Exception:
        provider = "twilio"

    # If singleton exists but different provider requested, rebuild
    if _telephony_singleton is None or (
        isinstance(_telephony_singleton, VonageProvider) and provider in ("twilio", "bland")
    ) or (
        isinstance(_telephony_singleton, TwilioProvider) and provider in ("vonage", "bland")
    ) or (
        isinstance(_telephony_singleton, BlandProvider) and provider in ("twilio", "vonage")
    ):
        logger.info(f"Initializing telephony provider: {provider}")
        if provider == "vonage":
            _telephony_singleton = VonageProvider(db)
        elif provider == "bland":
            _telephony_singleton = BlandProvider(db)
        elif provider == "telnyx":
            _telephony_singleton = TelnyxProvider(db)
        elif provider == "plivo":
            _telephony_singleton = PlivoProvider(db)
        elif provider == "signalwire":
            _telephony_singleton = SignalWireProvider(db)
        else:
            _telephony_singleton = TwilioProvider(db)
    return _telephony_singleton
