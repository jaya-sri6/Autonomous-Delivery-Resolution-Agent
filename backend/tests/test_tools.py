import pytest

from app.schemas import IncidentCreate, ResolutionAction
from app.tools.actions import execute_action
from app.tools.simulated import SimulatedBusinessSystems, ToolExecutionError, ToolRecorder


def test_traffic_tool_is_deterministic():
    recorder = ToolRecorder(SimulatedBusinessSystems())
    assert recorder.get_traffic_status("Downtown")["estimated_delay_minutes"] == 35
    assert recorder.get_traffic_status("Downtown")["estimated_delay_minutes"] == 35
    assert len(recorder.calls) == 2


def test_unknown_location_is_reported():
    with pytest.raises(ToolExecutionError):
        ToolRecorder(SimulatedBusinessSystems()).get_traffic_status("Nowhere")


def test_action_guard_rejects_unsupported_action():
    with pytest.raises(ValueError):
        execute_action(ToolRecorder(SimulatedBusinessSystems()), "delete_order", "ORD-1001")


def test_schema_strips_identifiers():
    incident = IncidentCreate(order_id=" ORD-1 ", merchant_id="m", partner_id="p", location="x", issue_type="traffic")
    assert incident.order_id == "ORD-1"
    assert ResolutionAction.UPDATE_DELIVERY_ETA.value == "update_delivery_eta"
