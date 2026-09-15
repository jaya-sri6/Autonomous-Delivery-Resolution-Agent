from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import IncidentRecord, ToolCallRecord, TraceRecord, utc_now
from ..schemas import IncidentCreate


def create_incident(db: Session, payload: IncidentCreate) -> IncidentRecord:
    now = utc_now()
    record = IncidentRecord(id=str(uuid4()), session_id=str(uuid4()), order_id=payload.order_id,
                            payload=payload.model_dump(mode="json"), status="created", retry_count=0,
                            created_at=now, updated_at=now)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_incident(db: Session, incident_id: str) -> IncidentRecord | None:
    return db.get(IncidentRecord, incident_id)


def update_incident(db: Session, record: IncidentRecord, **values: Any) -> IncidentRecord:
    for key, value in values.items():
        setattr(record, key, value)
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)
    return record


def add_trace(db: Session, incident_id: str, **values: Any) -> None:
    values.setdefault("payload", {})
    db.add(TraceRecord(incident_id=incident_id, timestamp=utc_now(), **values))
    db.commit()


def add_tool_call(db: Session, incident_id: str, record: dict[str, Any]) -> None:
    db.add(ToolCallRecord(incident_id=incident_id, tool_name=record["tool_name"], input=record["input"], output=record["output"],
                          success=record["success"], error=record["error"], timestamp=utc_now(), duration_ms=record["duration_ms"]))
    db.commit()


def traces_for(db: Session, incident_id: str) -> list[TraceRecord]:
    return list(db.scalars(select(TraceRecord).where(TraceRecord.incident_id == incident_id).order_by(TraceRecord.id)))


def tools_for(db: Session, incident_id: str) -> list[ToolCallRecord]:
    return list(db.scalars(select(ToolCallRecord).where(ToolCallRecord.incident_id == incident_id).order_by(ToolCallRecord.id)))
