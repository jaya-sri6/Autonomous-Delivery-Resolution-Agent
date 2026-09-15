from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class IncidentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    RESOLVED = "resolved"
    FAILED = "failed"
    ESCALATED = "escalated"


class ResolutionAction(StrEnum):
    REASSIGN_DELIVERY_PARTNER = "reassign_delivery_partner"
    UPDATE_DELIVERY_ETA = "update_delivery_eta"
    REQUEST_MERCHANT_PRIORITY = "request_merchant_priority"
    NOTIFY_CUSTOMER = "notify_customer"
    ESCALATE_INCIDENT = "escalate_incident"


class IncidentCreate(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    merchant_id: str = Field(min_length=1, max_length=100)
    partner_id: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=200)
    issue_type: str = Field(min_length=1, max_length=100)
    issue_severity: str = Field(default="medium", max_length=30)
    customer_priority: str = Field(default="standard", max_length=30)
    current_status: str = Field(default="in_transit", max_length=50)
    estimated_delivery_time: datetime | None = None
    traffic_condition: str | None = None
    weather_condition: str | None = None
    merchant_preparation_status: str | None = None

    @field_validator("order_id", "merchant_id", "partner_id", "location", "issue_type")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()


class IncidentRead(IncidentCreate):
    id: str
    status: IncidentStatus
    session_id: str
    created_at: datetime
    updated_at: datetime
    retry_count: int


class ResolutionDecision(BaseModel):
    action: ResolutionAction
    priority: str = Field(default="medium", max_length=30)
    reason: str = Field(min_length=1, max_length=2000)
    evidence: list[str] = Field(default_factory=list, max_length=20)
    expected_impact: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class VerificationResult(BaseModel):
    resolved: bool
    reason: str = Field(min_length=1, max_length=2000)
    remaining_risks: list[str] = Field(default_factory=list, max_length=20)
    next_action: ResolutionAction | None = None


class TraceEvent(BaseModel):
    event: str
    agent_name: str | None = None
    tool_name: str | None = None
    status: str
    message: str | None = None
    payload: dict = Field(default_factory=dict)
    timestamp: datetime
    duration_ms: float | None = None


class IncidentResolutionRead(BaseModel):
    incident_id: str
    decision: ResolutionDecision | None = None
    action_result: dict | None = None
    verification: VerificationResult | None = None
    reasoning_summary: str | None = None
    status: IncidentStatus


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
