import logging
from typing import Any

from sqlalchemy.orm import Session

from ..agents.planner import ResolutionPlanner
from ..config import Settings
from ..db import IncidentRecord
from ..graph.workflow import build_workflow
from ..repositories.incidents import add_tool_call, add_trace, update_incident
from ..schemas import IncidentCreate
from ..tools.simulated import SimulatedBusinessSystems, ToolRecorder

logger = logging.getLogger(__name__)
metrics = {"workflow_total": 0, "workflow_success_total": 0, "workflow_failure_total": 0, "tool_calls_total": 0}


def resolve_incident(db: Session, record: IncidentRecord, settings: Settings) -> dict[str, Any]:
    metrics["workflow_total"] += 1
    update_incident(db, record, status="running")
    add_trace(db, record.id, event="workflow_started", status="started", message="Autonomous resolution started")

    recorded_tools: list[dict[str, Any]] = []

    def on_tool_call(tool_record: dict[str, Any]) -> None:
        # LangGraph may run branches concurrently; persistence stays single-threaded.
        recorded_tools.append(tool_record)

    recorder = ToolRecorder(SimulatedBusinessSystems(), callback=on_tool_call)
    planner = ResolutionPlanner(settings.llm_provider, settings.openai_api_key, settings.openai_model)
    workflow = build_workflow(recorder, planner, settings.max_retry_count)
    try:
        result = workflow.invoke({"incident": record.payload, "session_id": record.session_id, "incident_id": record.id,
                                  "investigation_results": [], "tool_results": [], "errors": []})
        for tool_record in recorded_tools:
            metrics["tool_calls_total"] += 1
            add_tool_call(db, record.id, tool_record)
            add_trace(db, record.id, event="tool_called", tool_name=tool_record["tool_name"], status="success" if tool_record["success"] else "failure",
                      message=tool_record.get("error"), payload=tool_record.get("output", {}), duration_ms=tool_record.get("duration_ms"))
        for trace_event in result.get("trace_events", []):
            add_trace(db, record.id, event=trace_event["event"], agent_name=trace_event.get("agent_name"),
                      status=trace_event["status"], payload=trace_event.get("payload", {}))
        verification = result.get("verification_result")
        status = "resolved" if verification and verification.resolved else "escalated"
        resolution = {
            "decision": result.get("selected_resolution").model_dump(mode="json") if result.get("selected_resolution") else None,
            "action_result": result.get("action_result"),
            "verification": verification.model_dump(mode="json") if verification else None,
            "reasoning_summary": result.get("reasoning_summary"),
            "status": status,
        }
        update_incident(db, record, status=status, retry_count=result.get("retry_count", 0),
                        reasoning_summary=result.get("reasoning_summary"), resolution=resolution)
        add_trace(db, record.id, event="workflow_completed", status=status, message=result.get("reasoning_summary"), payload=resolution)
        metrics["workflow_success_total"] += int(status == "resolved")
        metrics["workflow_failure_total"] += int(status != "resolved")
        return resolution
    except Exception as exc:
        logger.exception("workflow_failed", extra={"incident_id": record.id, "session_id": record.session_id})
        update_incident(db, record, status="failed")
        add_trace(db, record.id, event="workflow_failed", status="failure", message=str(exc))
        metrics["workflow_failure_total"] += 1
        raise


def incident_as_dict(record: IncidentRecord) -> dict[str, Any]:
    return {**record.payload, "id": record.id, "session_id": record.session_id, "status": record.status,
            "retry_count": record.retry_count, "created_at": record.created_at, "updated_at": record.updated_at}
