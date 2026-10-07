from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# --- Incoming Message ---
class MessageRequest(BaseModel):
    message_id: str = Field(..., description="Unique WhatsApp message ID / wamid")
    rider_id: str = Field(..., description="Rider unique identifier e.g. R003")
    text: str = Field(..., description="Rider text message content")
    received_at: str = Field(..., description="ISO 8601 timestamp string")

class MessageResponse(BaseModel):
    reply: str = Field(..., description="Response reply text returned to rider")

# --- Agent Trace ---
class AgentTraceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rider_id: str
    message_id: Optional[str] = None
    step_name: str
    input_state: Optional[Dict[str, Any]] = None
    output_state: Optional[Dict[str, Any]] = None
    execution_log: Optional[str] = None
    timestamp: datetime

class RiderTraceResponse(BaseModel):
    rider_id: str
    total_traces: int
    traces: List[AgentTraceItem]

# --- Ops Approvals & Escalations ---
class PendingOpsItem(BaseModel):
    id: str
    type: str # "APPROVAL" or "ESCALATION"
    rider_id: str
    dispute_id: Optional[str] = None
    reason_or_notes: Optional[str] = None
    status: str
    created_at: datetime

class PendingOpsResponse(BaseModel):
    total_pending: int
    items: List[PendingOpsItem]

class OpsResolutionRequest(BaseModel):
    ops_user_id: str
    action: str # "APPROVE", "REJECT"
    notes: Optional[str] = None
