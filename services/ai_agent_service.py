"""
OpenAI AI Agent service for conducting account verification conversations.
"""
from openai import OpenAI
from typing import Optional, Dict, List
from schemas import CallContext, CallResultSchema, CallOutcome
from config import settings
import logging
import json

logger = logging.getLogger(__name__)


class AIAgentService:
    """Service for AI-powered account verification conversations."""
    
    SYSTEM_PROMPT = """You are calling to verify account information. BE DIRECT AND EFFICIENT.

**CRITICAL RULES:**
1. NEVER say "I'm an AI" or "automated assistant" - just say "Hello" and wait
2. Keep ALL responses under 5 words - be EXTREMELY brief
3. If you hear "transfer", "transferring", "hold", or "agent" → say "No thanks, goodbye" and END CALL
4. NO small talk, NO explanations, NO lengthy responses
5. Only provide information when directly asked
6. Get the info and END the call fast - max 60 seconds

**OPENING:**
When call connects: Just say "Hello" and WAIT. Let them talk first.

**RESPONSES:**
- When asked who you are: "Checking account info"
- When asked for details: Provide ONLY what's asked (e.g., "1234" for last 4 digits)
- When asked to confirm: "Yes" or "No" only
- If they start transferring: "No thanks, goodbye" then END CALL IMMEDIATELY

**WHAT TO COLLECT:**
1. Account status (active/closed/suspended)
2. Account holder name confirmation
3. Any alerts or issues

**HANG UP IMMEDIATELY IF:**
- You hear "transfer", "hold", "agent", "representative", "specialist"
- You get the account status
- Call goes over 60 seconds
- They ask for information you don't have

**MULTIPLE ACCOUNTS PER CALL:**
If you have multiple accounts to verify, ask to check them all at once:
"Can you check status for [NAME1] last 4: [XXXX] and [NAME2] last 4: [YYYY]?"

**OUTPUT FORMAT:**
{
  "account_exists": true/false,
  "account_details": {
    "status": "active/inactive/closed/suspended",
    "phone_match": true/false,
    "additional_notes": "..."
  },
  "verification_status": "verified|not_found|needs_human",
  "agent_notes": "Brief notes",
  "call_outcome": "account_found|account_not_found|needs_human|voicemail|failed",
  "follow_up_needed": true/false
}

BE FAST. NO WASTED TIME. Get info and hang up."""

    def __init__(self):
        # Use mock service in test mode
        if settings.test_mode:
            from services.mock_service import MockOpenAIService
            self._service = MockOpenAIService()
            logger.info("🧪 AIAgentService initialized in TEST MODE using mock service")
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self._service = None
            logger.info("🤖 AIAgentService initialized in LIVE MODE using real OpenAI API")
    
    def create_conversation_messages(self, call_context: CallContext) -> List[Dict[str, str]]:
        """Create the conversation messages for the AI agent."""
        context_prompt = call_context.to_prompt()
        
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": context_prompt},
        ]
    
    def process_conversation(
        self,
        call_context: CallContext,
        conversation_transcript: str
    ) -> tuple[CallResultSchema, str]:
        """
        Process the conversation and extract structured results.
        
        Args:
            call_context: Context for this call
            conversation_transcript: Full transcript of the conversation
        
        Returns:
            Tuple of (structured_result, summary)
        """
        # Use mock service in test mode
        if self._service:
            return self._service.process_conversation(call_context, conversation_transcript)
        
        try:
            extraction_prompt = f"""
Based on this phone call transcript, extract the structured information:

**Context:**
{call_context.to_prompt()}

**Transcript:**
{conversation_transcript}

**Task:**
Analyze the transcript and produce the required JSON output format with accurate information.
Determine if the account exists and extract any relevant details.
"""
            
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": extraction_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_json = json.loads(response.choices[0].message.content)
            
            # Parse into schema
            result = CallResultSchema(**result_json)
            
            # Generate human-readable summary
            summary = self._generate_summary(result, call_context)
            
            logger.info(f"Processed conversation for {call_context.verification_id}: {result.call_outcome}")
            return result, summary
            
        except Exception as e:
            logger.error(f"Failed to process conversation: {e}")
            return CallResultSchema(
                account_exists=False,
                verification_status="failed",
                agent_notes=f"Error processing conversation: {str(e)}",
                call_outcome=CallOutcome.FAILED,
                follow_up_needed=True
            ), f"Call failed: {str(e)}"
    
    def _generate_summary(self, result: CallResultSchema, context: CallContext) -> str:
        """Generate a human-readable summary of the call."""
        if result.call_outcome == CallOutcome.ACCOUNT_FOUND:
            details = result.account_details or {}
            status = details.get('status', 'unknown')
            return f"Account found for {context.customer_name} at {context.company_name}. Status: {status}"
        
        elif result.call_outcome == CallOutcome.ACCOUNT_NOT_FOUND:
            return f"No account found for {context.customer_name} at {context.company_name}"
        
        elif result.call_outcome == CallOutcome.NEEDS_VERIFICATION:
            return f"Account may exist but requires additional verification from customer"
        
        elif result.call_outcome == CallOutcome.NEEDS_HUMAN:
            return f"Human intervention needed: {result.agent_notes}"
        
        elif result.call_outcome == CallOutcome.VOICEMAIL:
            return f"Reached voicemail at {context.company_name}"
        
        elif result.call_outcome == CallOutcome.FAILED:
            return f"Call failed: {result.agent_notes}"
        
        else:
            return result.agent_notes or "Call completed"
    
    def simulate_conversation(self, call_context: CallContext) -> tuple[str, CallResultSchema, str]:
        """
        Simulate a conversation for testing (without actual call).
        
        Returns:
            Tuple of (transcript, result, summary)
        """
        transcript = f"""
[AI Agent]: Hi! This is an automated assistant calling to verify account information. 
We're checking if you have an account on file for {call_context.customer_name}. 
The phone number we have is {call_context.customer_phone}. 
Can you confirm if this account exists in your system?

[Business]: Let me check... Yes, I see an account here for {call_context.customer_name}.

[AI Agent]: Great! Can you confirm the phone number matches your records?

[Business]: Yes, {call_context.customer_phone} is on file. The account is active.

[AI Agent]: Perfect. Is there anything else I should know about this account?

[Business]: No, everything looks good. The account is in good standing.

[AI Agent]: Excellent. Thank you for your help!

[Business]: You're welcome, have a good day.
"""
        
        result = CallResultSchema(
            account_exists=True,
            account_details={
                "status": "active",
                "phone_match": True,
                "additional_notes": "Account in good standing"
            },
            verification_status="verified",
            agent_notes="Account verified successfully",
            call_outcome=CallOutcome.ACCOUNT_FOUND,
            follow_up_needed=False
        )
        
        summary = self._generate_summary(result, call_context)
        
        return transcript, result, summary


# Global AI agent service instance
ai_agent_service = AIAgentService()
