import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Float, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class ConversationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    PENDING_OPS = "PENDING_OPS"

class DisputeStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    INVESTIGATING = "INVESTIGATING"
    AUTO_APPROVED = "AUTO_APPROVED"
    AUTO_REJECTED = "AUTO_REJECTED"
    PENDING_OPS_APPROVAL = "PENDING_OPS_APPROVAL"
    OPS_APPROVED = "OPS_APPROVED"
    OPS_REJECTED = "OPS_REJECTED"
    ESCALATED = "ESCALATED"

class DecisionOutcome(str, enum.Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    REQUIRE_OPS_APPROVAL = "REQUIRE_OPS_APPROVAL"
    ESCALATE_TO_SUPPORT = "ESCALATE_TO_SUPPORT"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class Rider(Base):
    __tablename__ = "riders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True) # Normalized rider_id e.g. R003
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="rider")

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"), index=True)
    status: Mapped[ConversationStatus] = mapped_column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    rider: Mapped["Rider"] = relationship("Rider", back_populates="conversations")

class IncomingMessage(Base):
    __tablename__ = "incoming_messages"

    id: Mapped[str] = mapped_column(String(100), primary_key=True) # wamid / message_id
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ProcessedMessage(Base):
    __tablename__ = "processed_messages"

    message_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    rider_id: Mapped[str] = mapped_column(String(50), index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    response_reply: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED")

class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"), index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    dispute_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    claimed_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[DisputeStatus] = mapped_column(Enum(DisputeStatus), default=DisputeStatus.INITIATED)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ops_approvals: Mapped[list["OpsApproval"]] = relationship("OpsApproval", back_populates="dispute")
    escalations: Mapped[list["Escalation"]] = relationship("Escalation", back_populates="dispute")
    payment_decisions: Mapped[list["PaymentDecision"]] = relationship("PaymentDecision", back_populates="dispute")

class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"), index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="decision") # message_in, tool_call, decision, reply, error
    step_name: Mapped[str] = mapped_column(String(100))
    input_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    execution_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PaymentDecision(Base):
    __tablename__ = "payment_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dispute_id: Mapped[str] = mapped_column(String(36), ForeignKey("disputes.id"))
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"))
    decision: Mapped[DecisionOutcome] = mapped_column(Enum(DecisionOutcome))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dispute: Mapped["Dispute"] = relationship("Dispute", back_populates="payment_decisions")

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("payment_decisions.id"))
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"))
    payswift_transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class OpsApproval(Base):
    __tablename__ = "ops_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dispute_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("disputes.id"), nullable=True, index=True)
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"))
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    ops_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    dispute: Mapped[Optional["Dispute"]] = relationship("Dispute", back_populates="ops_approvals")

class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dispute_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("disputes.id"), nullable=True)
    rider_id: Mapped[str] = mapped_column(String(50), ForeignKey("riders.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    dispute: Mapped[Optional["Dispute"]] = relationship("Dispute", back_populates="escalations")
