"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from models import VerificationStatus, CallOutcome
import re


class AccountVerificationCreate(BaseModel):
    """Schema for creating a new account verification request."""
    verification_id: str
    customer_name: str
    customer_phone: str
    company_name: str
    company_phone: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    account_number: Optional[str] = None
    customer_date_of_birth: Optional[str] = None
    customer_ssn_last4: Optional[str] = None
    customer_ssn_full: Optional[str] = None  # Full SSN (XXX-XX-XXXX)
    additional_customer_info: Optional[Dict[str, str]] = None  # Any extra details
    verification_instruction: Optional[str] = None
    information_to_collect: Optional[List[str]] = None  # What to ask for
    priority: int = 0
    
    @field_validator('customer_phone', 'company_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate E.164 phone format."""
        if not re.match(r'^\+1\d{10}$', v):
            raise ValueError('Phone number must be in E.164 format: +1XXXXXXXXXX')
        return v


class AccountVerificationResponse(BaseModel):
    """Schema for account verification response."""
    verification_id: str
    customer_name: str
    customer_phone: str
    company_name: str
    company_phone: str
    customer_email: Optional[str]
    account_number: Optional[str]
    status: VerificationStatus
    attempt_count: int
    last_attempt_at: Optional[datetime]
    call_outcome: Optional[CallOutcome]
    account_exists: Optional[bool]
    account_details: Optional[Dict[str, Any]]
    call_summary: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CallResultSchema(BaseModel):
    """Schema for structured call outcome."""
    account_exists: bool
    account_details: Optional[Dict[str, str]] = None
    verification_status: str
    additional_info: Optional[str] = None
    agent_notes: str = ""
    call_outcome: CallOutcome
    follow_up_needed: bool = False


class CallContext(BaseModel):
    """Context passed to AI agent for each call."""
    verification_id: str
    customer_name: str
    customer_phone: str
    company_name: str
    company_phone: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    account_number: Optional[str] = None
    customer_date_of_birth: Optional[str] = None
    customer_ssn_last4: Optional[str] = None
    customer_ssn_full: Optional[str] = None  # Full SSN (XXX-XX-XXXX)
    additional_customer_info: Optional[Dict[str, str]] = None
    verification_instruction: Optional[str] = None
    information_to_collect: Optional[List[str]] = None
    attempt_number: int
    
    def to_prompt(self) -> str:
        """Convert to formatted prompt for AI agent."""
        info_parts = [
            f"- Customer Name: {self.customer_name}",
            f"- Customer Phone: {self.customer_phone}"
        ]
        
        if self.customer_email:
            info_parts.append(f"- Email: {self.customer_email}")
        if self.customer_address:
            info_parts.append(f"- Address: {self.customer_address}")
        if self.account_number:
            info_parts.append(f"- Account Number: {self.account_number}")
        if self.customer_date_of_birth:
            info_parts.append(f"- Date of Birth: {self.customer_date_of_birth}")
        if self.customer_ssn_full:
            info_parts.append(f"- SSN: {self.customer_ssn_full}")
        elif self.customer_ssn_last4:
            info_parts.append(f"- SSN Last 4: {self.customer_ssn_last4}")
        
        # Add any additional info
        if self.additional_customer_info:
            for key, value in self.additional_customer_info.items():
                info_parts.append(f"- {key}: {value}")
        
        customer_info = "\n".join(info_parts)
        
        instruction_str = ""
        if self.verification_instruction:
            instruction_str = f"\n\n**Special Instructions:**\n{self.verification_instruction}"
        
        collect_str = ""
        if self.information_to_collect:
            collect_str = f"\n\n**Information to Collect:**\n" + "\n".join([f"- {item}" for item in self.information_to_collect])
        
        return f"""
**Account Verification Context:**
{customer_info}

**Company to Call:** {self.company_name}
**Call Attempt:** #{self.attempt_number}{instruction_str}{collect_str}

**Your Mission:**
Call {self.company_name} to verify if they have an account for {self.customer_name}.
You have the customer information above that you can provide if the company asks for verification.
Only provide information that is listed above - if they ask for something you don't have, politely state you don't have that information.
Be professional and follow the conversation script.
"""


class BatchStartRequest(BaseModel):
    """Request to start a batch verification process."""
    max_verifications: Optional[int] = None


class SystemStats(BaseModel):
    """System statistics."""
    total_verifications: int
    pending: int
    calling: int
    verified: int
    not_found: int
    needs_human: int
    failed: int
    success_rate: float
    average_duration_seconds: Optional[float]


class ScheduleStatus(BaseModel):
    """Status of the automatic calling schedule."""
    is_running: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    total_processed: int
    total_successful: int
    total_failed: int
