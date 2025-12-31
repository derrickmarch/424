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
        self.from_number = "+18884821190"  # Mock number
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
        """
        # Generate a fake call SID
        call_sid = f"CA_MOCK_{int(time.time())}_{random.randint(1000, 9999)}"
        
        logger.info(f"🧪 MOCK CALL: Would call {to_number} for verification {verification_id}")
        logger.info(f"🧪 Mock Call SID: {call_sid}")
        logger.info(f"🧪 Webhook URL: {webhook_url}")
        logger.info(f"🧪 Status Callback: {status_callback_url}")
        
        return call_sid
    
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
        Return mock account balance information.
        """
        logger.info(f"🧪 MOCK: Returning mock balance information")
        return {
            'balance': '15.50',
            'currency': 'USD',
            'account_status': 'active',
            'friendly_name': 'Test Account (Mock Mode)',
            'usage': {
                'total_calls': 0,
                'total_minutes': 0.0,
                'period_start': None,
                'period_end': None
            }
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
        from schemas import CallResult
        from models import CallOutcome, VerificationStatus
        
        logger.info(f"🧪 MOCK AI: Processing conversation for {call_context.customer_name}")
        logger.info(f"🧪 Mock transcript length: {len(conversation_transcript)} chars")
        
        # Simulate different outcomes randomly for testing
        outcomes = [
            {
                'call_outcome': CallOutcome.ACCOUNT_FOUND,
                'verification_status': VerificationStatus.VERIFIED,
                'account_exists': True,
                'notes': '🧪 MOCK: Account verified successfully (simulated)',
                'summary': 'Mock AI confirmed account exists for testing purposes.'
            },
            {
                'call_outcome': CallOutcome.ACCOUNT_NOT_FOUND,
                'verification_status': VerificationStatus.NOT_FOUND,
                'account_exists': False,
                'notes': '🧪 MOCK: Account not found (simulated)',
                'summary': 'Mock AI could not find account for testing purposes.'
            },
            {
                'call_outcome': CallOutcome.HUMAN_NEEDED,
                'verification_status': VerificationStatus.NEEDS_HUMAN,
                'account_exists': None,
                'notes': '🧪 MOCK: Needs human review (simulated)',
                'summary': 'Mock AI determined human review needed for testing.'
            }
        ]
        
        # Pick a random outcome for variety in testing
        mock_outcome = random.choice(outcomes)
        
        result = CallResult(
            call_outcome=mock_outcome['call_outcome'],
            verification_status=mock_outcome['verification_status'],
            account_exists=mock_outcome['account_exists'],
            agent_notes=mock_outcome['notes']
        )
        
        summary = mock_outcome['summary']
        
        logger.info(f"🧪 MOCK AI Result: {result.call_outcome.value} - {result.verification_status.value}")
        
        return result, summary
