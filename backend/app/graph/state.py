import operator
from datetime import datetime
from typing import Annotated, Any, TypedDict

from ..schemas import ResolutionDecision, VerificationResult


class WorkflowState(TypedDict, total=False):
    incident: dict[str, Any]
    session_id: str
    incident_id: str
    investigation_results: Annotated[list[dict[str, Any]], operator.add]
    tool_results: Annotated[list[dict[str, Any]], operator.add]
    selected_resolution: ResolutionDecision | None
    action_result: dict[str, Any] | None
    verification_result: VerificationResult | None
    reasoning_summary: str | None
    status: str
    retry_count: int
    max_retry_count: int
    timestamps: dict[str, datetime]
    errors: Annotated[list[str], operator.add]
    trace_events: Annotated[list[dict[str, Any]], operator.add]
