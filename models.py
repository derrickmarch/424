"""
SQLAlchemy models for the Account Verifier system.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class VerificationStatus(str, enum.Enum):
    """Account verification status."""
    PENDING = "pending"
    CALLING = "calling"
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    NEEDS_HUMAN = "needs_human"
    FAILED = "failed"


class AccountStatus(str, enum.Enum):
    """Customer record verification status for Citibank checking."""
    UNCHECKED = "unchecked"  # Not yet verified
    VALID = "valid"  # Account found (CASE 3)
    INVALID = "invalid"  # Account not found (CASE 2)
    CHECKING = "checking"  # Currently being checked
    FAILED = "failed"  # Call failed/error occurred


class CallOutcome(str, enum.Enum):
    """Call outcome types."""
    ACCOUNT_FOUND = "account_found"
    ACCOUNT_NOT_FOUND = "account_not_found"
    NEEDS_VERIFICATION = "needs_verification"
    NEEDS_HUMAN = "needs_human"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    FAILED = "failed"
    BUSY = "busy"


class AccountVerification(Base):
    """Account verification model."""
    
    __tablename__ = "account_verifications"
    
    # Primary fields
    verification_id = Column(String(255), primary_key=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)  # Phone to provide to company
    company_name = Column(String(255), nullable=False)
    company_phone = Column(String(20), nullable=False)  # Company's phone number to call
    
    # Optional additional info to verify
    customer_email = Column(String(255), nullable=True)
    customer_address = Column(Text, nullable=True)
    account_number = Column(String(255), nullable=True)  # If known
    customer_date_of_birth = Column(String(50), nullable=True)
    customer_ssn_last4 = Column(String(4), nullable=True)  # Last 4 digits of SSN
    customer_ssn_full = Column(String(11), nullable=True)  # Full SSN (XXX-XX-XXXX format)
    
    # Additional details the agent can provide if asked
    additional_customer_info = Column(JSON, nullable=True)  # Flexible key-value pairs
    
    # Instructions
    verification_instruction = Column(Text, nullable=True)  # Special instructions
    information_to_collect = Column(JSON, nullable=True)  # Specific info to ask for
    
    # Status tracking
    status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    
    # Call metadata
    call_sid = Column(String(255), nullable=True)
    call_duration_seconds = Column(Integer, nullable=True)
    
    # Results
    result_json = Column(JSON, nullable=True)
    call_summary = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    call_outcome = Column(SQLEnum(CallOutcome), nullable=True)
    
    # Account details (if found)
    account_exists = Column(Boolean, nullable=True)
    account_details = Column(JSON, nullable=True)  # Store any account info retrieved
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Additional flags
    follow_up_needed = Column(Boolean, default=False)
    recording_consent_given = Column(Boolean, nullable=True)
    priority = Column(Integer, default=0)


class CallLog(Base):
    """Detailed call logs for auditing and debugging."""
    
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    verification_id = Column(String(255), nullable=False, index=True)
    call_sid = Column(String(255), nullable=True, index=True)
    
    # Call details
    direction = Column(String(20), nullable=False)  # outbound
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    
    # Status and outcome
    call_status = Column(String(50), nullable=True)
    call_outcome = Column(SQLEnum(CallOutcome), nullable=True)
    
    # Timing
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    answered_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Content
    conversation_log = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    attempt_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Blocklist(Base):
    """Track numbers that requested not to be called."""
    
    __tablename__ = "blocklist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_by = Column(String(255), nullable=True)


class BatchStatus(str, enum.Enum):
    """Batch processing status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class CallSchedule(Base):
    """Track the automatic calling schedule."""
    
    __tablename__ = "call_schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    verifications_processed = Column(Integer, default=0)
    verifications_successful = Column(Integer, default=0)
    verifications_failed = Column(Integer, default=0)
    is_running = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BatchProcess(Base):
    """Track real-time batch processing status."""
    
    __tablename__ = "batch_processes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Status
    status = Column(SQLEnum(BatchStatus), default=BatchStatus.IDLE, nullable=False)
    
    # Progress tracking
    total_verifications = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    successful_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Current call info
    current_verification_id = Column(String(255), nullable=True)
    current_call_sid = Column(String(255), nullable=True)
    current_customer_name = Column(String(255), nullable=True)
    current_company_name = Column(String(255), nullable=True)
    
    # Live transcription
    live_transcript = Column(Text, nullable=True)
    
    # Logs
    logs = Column(JSON, nullable=True)  # Array of log entries
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    triggered_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(Base):
    """User accounts for system access."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")


class AuditLog(Base):
    """Audit log for tracking all system actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # create, update, delete, view, etc.
    resource_type = Column(String(50), nullable=False)  # verification, user, setting, etc.
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)  # Additional details as JSON
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")


class SystemSettings(Base):
    """System-wide settings stored in database."""
    
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=True)
    setting_type = Column(String(50), default="string")  # string, int, bool, json
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)  # Don't show in UI
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(100), nullable=True)


class CustomerRecord(Base):
    """Customer records for Citibank SSN/Credit Card verification."""
    
    __tablename__ = "customer_records"
    
    record_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Customer identifiers (from CSV)
    customer_id = Column(String(100), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)
    ssn = Column(String(11), nullable=False, index=True)  # Full 9-digit SSN (format: 123-45-6789)
    credit_card_number = Column(String(50), nullable=False, index=True)
    
    # Additional customer info
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    
    # Verification status
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.UNCHECKED, nullable=False, index=True)
    
    # Call tracking
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Results
    verification_result = Column(Text, nullable=True)  # Notes from the call
    call_sid = Column(String(255), nullable=True)
    
    # Additional metadata
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)  # Higher = process first
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
