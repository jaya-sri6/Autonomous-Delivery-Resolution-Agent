from app.agents.planner import ResolutionPlanner
from app.graph.workflow import build_workflow
from app.tools.simulated import SimulatedBusinessSystems, ToolRecorder


def test_partner_unavailable_resolves_with_reassignment():
    recorder = ToolRecorder(SimulatedBusinessSystems())
    graph = build_workflow(recorder, ResolutionPlanner())
    result = graph.invoke({"incident": {"order_id":"ORD-1003","merchant_id":"MERCHANT-READY","partner_id":"PARTNER-BUSY","location":"Airport","issue_type":"partner_unavailable","issue_severity":"high","customer_priority":"standard"}, "retry_count": 0, "investigation_results": [], "tool_results": [], "errors": []})
    assert result["selected_resolution"].action.value == "reassign_delivery_partner"
    assert result["verification_result"].resolved is True
    assert len(recorder.calls) == 6


def test_address_problem_is_bounded():
    recorder = ToolRecorder(SimulatedBusinessSystems())
    graph = build_workflow(recorder, ResolutionPlanner(), max_retry_count=2)
    result = graph.invoke({"incident": {"order_id":"ORD-1004","merchant_id":"MERCHANT-READY","partner_id":"PARTNER-AVAILABLE","location":"Unknown Address","issue_type":"address_problem","issue_severity":"high","customer_priority":"high"}, "retry_count": 0, "investigation_results": [], "tool_results": [], "errors": []})
    assert result["verification_result"].resolved is False
    assert result["retry_count"] == 2
