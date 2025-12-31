"""
Mock service for testing mode - simulates Twilio and OpenAI calls without using real APIs
"""
import logging
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MockTwilioService:
    """Mock Twilio service for testing mode."""
    
    def __init__(self):
        self.from_number = "+15551234567"  # Mock number
        logger.info("🧪 Mock Twilio Service initialized (TEST MODE)")
    
    def make_outbound_call(
        self,
        to_number: str,
        verification_id: str,
        webhook_url: str,
        status_callback_url: str
    ) -> str:
        """
        Simulate an outbound call without actually calling Twilio.
        In test mode, always calls the registered test number for Twilio trial account compliance.
        """
        from config import settings
        # In test mode, override the number to always call the verified test number
        test_number = settings.test_phone_number
        actual_to_number = test_number
        
        # Generate a fake call SID
        call_sid = f"CA_MOCK_{int(time.time())}_{random.randint(1000, 9999)}"
        
        logger.info(f"🧪 MOCK CALL: Original target: {to_number}, Calling test number: {actual_to_number}")
        logger.info(f"🧪 Mock Call SID: {call_sid}")
        logger.info(f"🧪 Verification ID: {verification_id}")
        logger.info(f"🧪 Webhook URL: {webhook_url}")
        logger.info(f"🧪 Status Callback: {status_callback_url}")
        logger.info(f"🧪 NOTE: Test mode always calls {test_number} (registered number) for Twilio trial compliance")
        
        # Schedule automatic call completion after a short delay
        self._schedule_mock_completion(call_sid, verification_id)
        
        return call_sid
    
    def _schedule_mock_completion(self, call_sid: str, verification_id: str):
        """Schedule a background task to simulate call completion."""
        import threading
        
        def simulate_call():
            """Simulate call completion after a delay."""
            time.sleep(random.randint(3, 8))  # Random delay 3-8 seconds
            
            logger.info(f"🧪 MOCK: Simulating completion for call {call_sid}")
            
            # Trigger the completion handler
            try:
                from database import get_db
                from services.call_orchestrator import CallOrchestrator
                
                db = next(get_db())
                orchestrator = CallOrchestrator(db)
                
                # Generate a mock transcript
                mock_transcript = self._generate_mock_transcript(verification_id)
                mock_duration = random.randint(30, 120)
                
                orchestrator.handle_call_completed(
                    call_sid=call_sid,
                    conversation_transcript=mock_transcript,
                    call_duration=mock_duration,
                    recording_consent_given=True
                )
                
                logger.info(f"🧪 MOCK: Completed call {call_sid} successfully")
                
            except Exception as e:
                logger.error(f"🧪 MOCK: Error completing call {call_sid}: {e}", exc_info=True)
        
        # Start background thread
        thread = threading.Thread(target=simulate_call, daemon=True)
        thread.start()
    
    def _generate_mock_transcript(self, verification_id: str) -> str:
        """Generate a mock conversation transcript."""
        templates = [
            f"[Agent]: Hello, this is the automated verification system calling about account verification.\n[Representative]: Yes, hello. How can I help you?\n[Agent]: I'm calling to verify an account. Could you confirm if you have an account for the customer?\n[Representative]: Let me check... Yes, I can confirm we have that account on file.\n[Agent]: Thank you for confirming. The account has been verified.\n[Representative]: You're welcome. Have a good day.",
            
            f"[Agent]: Hello, this is an automated call regarding account verification.\n[Representative]: Hi there.\n[Agent]: I need to verify if an account exists in your system.\n[Representative]: I've checked our records and I don't see that account.\n[Agent]: Understood. Thank you for checking.\n[Representative]: No problem.",
            
            f"[Agent]: Good day, I'm calling about an account verification.\n[Representative]: Hello. What do you need?\n[Agent]: Can you verify if you have an account on file?\n[Representative]: This is a complex situation. You might need to speak with a supervisor.\n[Agent]: I understand. This will require human review.\n[Representative]: Yes, please have someone call back."
        ]
        
        return random.choice(templates)
    
    def generate_stream_twiml(self, stream_url: str) -> str:
        """Generate mock TwiML."""
        logger.info(f"🧪 MOCK: Generated TwiML for stream: {stream_url}")
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="' + stream_url + '"/></Connect></Response>'
    
    def generate_voicemail_twiml(self, message: Optional[str] = None) -> str:
        """Generate mock voicemail TwiML."""
        logger.info(f"🧪 MOCK: Generated voicemail TwiML")
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
    
    def get_call_status(self, call_sid: str) -> dict:
        """Get mock call status."""
        logger.info(f"🧪 MOCK: Fetching status for call {call_sid}")
        return {
            'sid': call_sid,
            'status': 'completed',
            'duration': random.randint(30, 180),
            'start_time': None,
            'end_time': None,
        }
    
    def hangup_call(self, call_sid: str) -> bool:
        """Simulate hanging up a call."""
        logger.info(f"🧪 MOCK: Hung up call {call_sid}")
        return True
    
    def get_account_balance(self) -> dict:
        """
        Fetch REAL Twilio account balance even in test mode.
        This allows viewing actual Twilio account information while preventing real calls to unverified numbers.
        For trial accounts, some features may be limited.
        """
        try:
            from config import settings
            from twilio.rest import Client
            from datetime import datetime, timedelta
            
            logger.info(f"🧪 MOCK: Fetching REAL Twilio account information from your Twilio account")
            
            # Create a real Twilio client to fetch balance
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            
            # Try to fetch account info (this should work for trial accounts)
            account_sid = client.account_sid
            account = client.api.accounts(account_sid).fetch()
            
            # Try to fetch balance (may fail on trial accounts)
            balance_value = "Trial Account"
            currency = "USD"
            try:
                balance = client.balance.fetch()
                balance_value = str(balance.balance)
                currency = str(balance.currency)
            except Exception as balance_error:
                logger.info(f"🧪 MOCK: Balance API not available (trial account): {balance_error}")
                # For trial accounts, Twilio provides limited balance info
                balance_value = "Trial Credit Available"
            
            # Try to fetch usage (may be limited on trial accounts)
            total_call_count = 0
            total_call_minutes = 0.0
            usage_start = None
            usage_end = None
            
            try:
                today = datetime.now()
                start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Get voice usage
                voice_usage = client.usage.records.list(
                    category='calls-inbound,calls-outbound',
                    start_date=start_of_month.date(),
                    end_date=today.date(),
                    limit=10
                )
                
                for record in voice_usage:
                    total_call_minutes += float(record.usage)
                    total_call_count += int(record.count) if hasattr(record, 'count') else 0
                
                usage_start = start_of_month.isoformat()
                usage_end = today.isoformat()
            except Exception as usage_error:
                logger.info(f"🧪 MOCK: Usage API not available (trial account): {usage_error}")
            
            logger.info(f"🧪 MOCK: Account Status: {account.status}")
            logger.info(f"🧪 MOCK: Account Type: {account.type}")
            logger.info(f"🧪 MOCK: Balance: {balance_value} {currency}")
            
            account_type_msg = "Trial/Test Account" if account.status == "active" and "trial" in account.type.lower() else account.type
            
            return {
                'balance': balance_value,
                'currency': currency,
                'account_status': account.status,
                'friendly_name': f"{account.friendly_name} (TEST MODE 🧪)",
                'account_type': account_type_msg,
                'usage': {
                    'total_calls': total_call_count,
                    'total_minutes': round(total_call_minutes, 2),
                    'period_start': usage_start,
                    'period_end': usage_end
                },
                'note': f'Test mode: Calls will only go to verified number ({settings.test_phone_number})'
            }
            
        except Exception as e:
            logger.error(f"🧪 MOCK: Failed to fetch Twilio account info: {e}")
            # Fallback to basic info if Twilio API fails
            return {
                'balance': 'Trial Account',
                'currency': 'USD',
                'account_status': 'active',
                'friendly_name': 'Twilio Test Account (TEST MODE 🧪)',
                'account_type': 'Trial',
                'usage': {
                    'total_calls': 0,
                    'total_minutes': 0.0,
                    'period_start': None,
                    'period_end': None
                },
                'note': f'Test mode: Calls will only go to verified number ({settings.test_phone_number})',
                'error': str(e)
            }


class MockOpenAIService:
    """Mock OpenAI service for testing mode."""
    
    def __init__(self):
        logger.info("🧪 Mock OpenAI Service initialized (TEST MODE)")
    
    def process_conversation(self, call_context, conversation_transcript: str) -> tuple:
        """
        Simulate AI processing of conversation.
        Returns mock result similar to real AI agent.
        """
        from schemas import CallResultSchema
        from models import CallOutcome, VerificationStatus
        
        logger.info(f"🧪 MOCK AI: Processing conversation for {call_context.customer_name}")
        logger.info(f"🧪 Mock transcript length: {len(conversation_transcript)} chars")
        
        # Simulate different outcomes randomly for testing
        outcomes = [
            {
                'call_outcome': CallOutcome.ACCOUNT_FOUND,
                'verification_status': 'verified',
                'account_exists': True,
                'account_details': {'status': 'active', 'phone_match': True},
                'notes': '🧪 MOCK: Account verified successfully (simulated)',
                'summary': 'Mock AI confirmed account exists for testing purposes.',
                'follow_up_needed': False
            },
            {
                'call_outcome': CallOutcome.ACCOUNT_NOT_FOUND,
                'verification_status': 'not_found',
                'account_exists': False,
                'account_details': None,
                'notes': '🧪 MOCK: Account not found (simulated)',
                'summary': 'Mock AI could not find account for testing purposes.',
                'follow_up_needed': False
            },
            {
                'call_outcome': CallOutcome.NEEDS_HUMAN,
                'verification_status': 'needs_human',
                'account_exists': None,
                'account_details': None,
                'notes': '🧪 MOCK: Needs human review (simulated)',
                'summary': 'Mock AI determined human review needed for testing.',
                'follow_up_needed': True
            }
        ]
        
        # Pick a random outcome for variety in testing
        mock_outcome = random.choice(outcomes)
        
        result = CallResultSchema(
            call_outcome=mock_outcome['call_outcome'],
            verification_status=mock_outcome['verification_status'],
            account_exists=mock_outcome['account_exists'],
            account_details=mock_outcome['account_details'],
            agent_notes=mock_outcome['notes'],
            follow_up_needed=mock_outcome['follow_up_needed']
        )
        
        summary = mock_outcome['summary']
        
        logger.info(f"🧪 MOCK AI Result: {result.call_outcome.value} - {result.verification_status}")
        
        return result, summary
