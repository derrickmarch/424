"""
Simple smoke tests for telephony providers.
Run: python -m scripts.smoke_test
"""
from database import get_db_context, init_db
from services.telephony import get_telephony_service
from services.verification_service import VerificationService
from services.settings_service import get_runtime_settings
from config import settings


def main():
    init_db()
    with get_db_context() as db:
        runtime = get_runtime_settings(db)
        provider = (runtime.get("telephony_provider", "twilio") or "twilio").lower()
        print(f"Active provider: {provider}")
        telephony = get_telephony_service(db)
        # Balance
        bal = telephony.get_account_balance()
        print("Balance:", bal)
        # From number
        print("From number:", telephony.get_from_number())
        # Do not place real calls; just report readiness
        # Verify webhook base resolution via orchestrator helper logic requires a verification id; we skip real call
        # Provider/mode hints
        is_test = settings.get_test_mode()
        if provider == "bland":
            print(f"Smoke test complete. TEST_MODE={is_test}. In test mode, Bland still places live calls if BLAND_API_KEY is set; set BLAND_WEBHOOK_BASE_URL to your ngrok URL.")
        elif provider == "vonage":
            print(f"Smoke test complete. TEST_MODE={is_test}. In test mode, Vonage uses mock behavior.")
        else:
            print(f"Smoke test complete. TEST_MODE={is_test}. Twilio uses normal logic (mock only via MockTwilioService code paths).")


if __name__ == "__main__":
    main()
