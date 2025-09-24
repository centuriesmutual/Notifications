"""
Data models for the Centuries Mutual Home App
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MessageType(str, Enum):
    """Message types for the notification system"""
    DOCUMENT_REQUEST = "document_request"
    CLAIM_UPDATE = "claim_update"
    PAYMENT_REMINDER = "payment_reminder"
    ENROLLMENT_NOTIFICATION = "enrollment_notification"
    BENEFICIARY_UPDATE = "beneficiary_update"
    SYSTEM_ALERT = "system_alert"


class DocumentType(str, Enum):
    """Document types for the system"""
    ENROLLMENT_FORM = "enrollment_form"
    CLAIMS_FORM = "claims_form"
    BENEFICIARY_FORM = "beneficiary_form"
    POLICY_DOCUMENT = "policy_document"
    PAYMENT_RECEIPT = "payment_receipt"
    AUDIT_REPORT = "audit_report"


class MessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    ARCHIVED = "archived"


# SQLAlchemy Models
class Client(Base):
    """Client database model"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict)


class Message(Base):
    """Message database model"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(100), unique=True, index=True, nullable=False)
    client_id = Column(String(50), index=True, nullable=False)
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), default=MessageStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, default=dict)


class Document(Base):
    """Document database model"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), unique=True, index=True, nullable=False)
    client_id = Column(String(50), index=True, nullable=False)
    document_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    shared_link = Column(String(1000), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)


class AuditLog(Base):
    """Audit log database model"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), index=True, nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    metadata = Column(JSON, default=dict)


# Pydantic Models for API
class ClientCreate(BaseModel):
    """Client creation model"""
    client_id: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, max_length=20)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ClientResponse(BaseModel):
    """Client response model"""
    id: int
    client_id: str
    email: str
    phone: Optional[str]
    first_name: str
    last_name: str
    created_at: datetime
    is_active: bool
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Message creation model"""
    client_id: str = Field(..., min_length=3, max_length=50)
    message_type: MessageType
    content: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Message response model"""
    id: int
    message_id: str
    client_id: str
    message_type: MessageType
    content: str
    status: MessageStatus
    created_at: datetime
    delivered_at: Optional[datetime]
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """Document creation model"""
    client_id: str = Field(..., min_length=3, max_length=50)
    document_type: DocumentType
    file_data: bytes
    filename: str = Field(..., min_length=1, max_length=255)
    expires_hours: Optional[int] = Field(default=24, ge=1, le=168)  # 1 hour to 1 week


class DocumentResponse(BaseModel):
    """Document response model"""
    id: int
    document_id: str
    client_id: str
    document_type: DocumentType
    file_path: str
    file_size: int
    shared_link: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    access_count: int
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Webhook payload model"""
    event_type: str
    client_id: str
    resource_id: str
    timestamp: datetime
    metadata: Dict[str, Any]
