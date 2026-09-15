from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..repositories.incidents import get_incident, create_incident, traces_for, tools_for
from ..schemas import HealthResponse, IncidentCreate
from ..services.incident_service import incident_as_dict, metrics, resolve_incident

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", database="configured", redis="optional")


@router.get("/metrics")
def get_metrics() -> dict:
    return metrics


@router.post("/incidents")
def create(payload: IncidentCreate, db: Session = Depends(get_db)) -> dict:
    return incident_as_dict(create_incident(db, payload))


def _required(db: Session, incident_id: str):
    record = get_incident(db, incident_id)
    if not record:
        raise HTTPException(status_code=404, detail="Incident not found")
    return record


@router.post("/incidents/{incident_id}/resolve")
def resolve(incident_id: str, db: Session = Depends(get_db)) -> dict:
    record = _required(db, incident_id)
    if record.status == "resolved" and record.resolution:
        return record.resolution
    return resolve_incident(db, record, get_settings())


@router.get("/incidents/{incident_id}")
def details(incident_id: str, db: Session = Depends(get_db)) -> dict:
    return incident_as_dict(_required(db, incident_id))


@router.get("/incidents/{incident_id}/trace")
def trace(incident_id: str, db: Session = Depends(get_db)) -> list[dict]:
    _required(db, incident_id)
    return [{"event": item.event, "agent_name": item.agent_name, "tool_name": item.tool_name, "status": item.status,
             "message": item.message, "payload": item.payload, "timestamp": item.timestamp, "duration_ms": item.duration_ms} for item in traces_for(db, incident_id)]


@router.get("/incidents/{incident_id}/tools")
def tools(incident_id: str, db: Session = Depends(get_db)) -> list[dict]:
    _required(db, incident_id)
    return [{"tool_name": item.tool_name, "input": item.input, "output": item.output, "success": item.success,
             "error": item.error, "timestamp": item.timestamp, "duration_ms": item.duration_ms} for item in tools_for(db, incident_id)]


@router.get("/incidents/{incident_id}/resolution")
def resolution(incident_id: str, db: Session = Depends(get_db)) -> dict:
    record = _required(db, incident_id)
    return record.resolution or {"status": record.status, "decision": None}
