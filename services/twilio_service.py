"""
Twilio integration service for making calls and handling webhooks.
"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from config import settings
import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for Twilio voice operations."""
    
    def __init__(self, db: Session = None):
        """
        Initialize Twilio service.
        
        Args:
            db: Database session for runtime settings (optional, will use env vars if not provided)
        """
        self.db = db
        
        # Get credentials (from database if available, otherwise from env)
        if db:
            from services.settings_service import get_runtime_settings
            runtime = get_runtime_settings(db)
            account_sid = runtime.get_twilio_account_sid()
            auth_token = runtime.get_twilio_auth_token()
            phone_number = runtime.get_twilio_phone_number()
        else:
            account_sid = settings.twilio_account_sid
            auth_token = settings.twilio_auth_token
            phone_number = settings.twilio_phone_number
        
        # Use mock service in test mode (check runtime override)
        test_mode = settings.get_test_mode()
        if test_mode:
            from services.mock_service import MockTwilioService
            self._service = MockTwilioService()
            self.from_number = phone_number
            logger.info("🧪 TwilioService initialized in TEST MODE using mock service")
        else:
            self.client = Client(account_sid, auth_token)
            self.from_number = phone_number
            self._service = None
            logger.info("📞 TwilioService initialized in LIVE MODE using real Twilio API")
    
    def refresh_credentials(self, db: Session):
        """Refresh credentials from database (allows hot-reload of API keys)."""
        test_mode = settings.get_test_mode()
        if test_mode:
            return  # No need to refresh in test mode
        
        from services.settings_service import get_runtime_settings
        runtime = get_runtime_settings(db)
        account_sid = runtime.get_twilio_account_sid()
        auth_token = runtime.get_twilio_auth_token()
        phone_number = runtime.get_twilio_phone_number()
        
        self.client = Client(account_sid, auth_token)
        self.from_number = phone_number
        logger.info("🔄 Twilio credentials refreshed from database")
    
    def make_outbound_call(
        self,
        to_number: str,
        verification_id: str,
        webhook_url: str,
        status_callback_url: str
    ) -> str:
        """
        Initiate an outbound call.
        
        Args:
            to_number: The company phone number to call
            verification_id: Verification ID for tracking
            webhook_url: URL to receive TwiML instructions when call is answered
            status_callback_url: URL to receive call status updates
        
        Returns:
            call_sid: Twilio Call SID
        """
        # Use mock service in test mode
        if self._service:
            return self._service.make_outbound_call(to_number, verification_id, webhook_url, status_callback_url)
        
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=webhook_url,
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                timeout=30,
                record=False,  # No call recording for account verification
                machine_detection='Enable',
            )
            
            logger.info(f"Initiated call {call.sid} to {to_number} for verification {verification_id}")
            return call.sid
            
        except Exception as e:
            logger.error(f"Failed to initiate call to {to_number}: {e}")
            raise
    
    def generate_stream_twiml(self, stream_url: str) -> str:
        """Generate TwiML to start a Media Stream."""
        response = VoiceResponse()
        connect = Connect()
        stream = Stream(url=stream_url)
        connect.append(stream)
        response.append(connect)
        return str(response)
    
    def generate_voicemail_twiml(self, message: Optional[str] = None) -> str:
        """Generate TwiML to leave a voicemail message or just hang up."""
        response = VoiceResponse()
        if message:
            response.say(message, voice='Polly.Joanna')
        response.hangup()
        return str(response)
    
    def get_call_status(self, call_sid: str) -> dict:
        """Get current status of a call."""
        # Use mock service in test mode
        if self._service:
            return self._service.get_call_status(call_sid)
        
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'start_time': call.start_time,
                'end_time': call.end_time,
            }
        except Exception as e:
            logger.error(f"Failed to fetch call status for {call_sid}: {e}")
            raise
    
    def hangup_call(self, call_sid: str) -> bool:
        """Hang up an active call."""
        # Use mock service in test mode
        if self._service:
            return self._service.hangup_call(call_sid)
        
        try:
            call = self.client.calls(call_sid).update(status='completed')
            logger.info(f"Hung up call {call_sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to hang up call {call_sid}: {e}")
            return False
    
    def get_account_balance(self) -> dict:
        """
        Get Twilio account balance and usage information.
        
        Returns:
            dict: Account balance, currency, and usage statistics
        """
        # Use mock service in test mode
        if self._service:
            return self._service.get_account_balance()
        
        try:
            # Fetch account balance
            # Get account SID from client
            account_sid = self.client.account_sid
            account = self.client.api.accounts(account_sid).fetch()
            balance = self.client.balance.fetch()
            
            # Fetch usage for current month (calls)
            from datetime import datetime, timedelta
            today = datetime.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get call usage statistics for current month
            calls_usage = self.client.usage.records.list(
                category='calls',
                start_date=start_of_month.date(),
                end_date=today.date(),
                limit=1
            )
            
            # Get total call duration in minutes
            total_minutes = 0
            total_count = 0
            if calls_usage:
                for record in calls_usage:
                    total_minutes += float(record.usage)  # Usage is in minutes
                    total_count = int(record.count) if hasattr(record, 'count') else 0
            
            # Get voice usage with more details
            # Twilio Usage API does not accept comma-separated categories; query separately and aggregate.
            inbound_usage = self.client.usage.records.list(
                category='calls-inbound',
                start_date=start_of_month.date(),
                end_date=today.date(),
                limit=100
            )
            outbound_usage = self.client.usage.records.list(
                category='calls-outbound',
                start_date=start_of_month.date(),
                end_date=today.date(),
                limit=100
            )

            total_call_count = 0
            total_call_minutes = 0.0
            for record in list(inbound_usage) + list(outbound_usage):
                try:
                    total_call_minutes += float(getattr(record, 'usage', 0) or 0)
                except Exception:
                    pass
                try:
                    total_call_count += int(getattr(record, 'count', 0) or 0)
                except Exception:
                    pass

            return {
                'balance': str(balance.balance),
                'currency': str(balance.currency),
                'account_status': account.status,
                'friendly_name': account.friendly_name,
                'usage': {
                    'total_calls': total_call_count,
                    'total_minutes': round(total_call_minutes, 2),
                    'period_start': start_of_month.isoformat(),
                    'period_end': today.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch Twilio account balance: {e}")
            return {
                'balance': 'N/A',
                'currency': 'USD',
                'account_status': 'unknown',
                'friendly_name': 'N/A',
                'usage': {
                    'total_calls': 0,
                    'total_minutes': 0,
                    'period_start': None,
                    'period_end': None
                },
                'error': str(e)
            }


# Global Twilio service instance - lazy initialization
_twilio_service = None

def get_twilio_service(db: Session = None) -> TwilioService:
    """Get or create Twilio service instance with optional database for runtime settings."""
    global _twilio_service
    if _twilio_service is None or db is not None:
        _twilio_service = TwilioService(db)
    return _twilio_service

# Initialize global instance on module import
twilio_service = get_twilio_service()
