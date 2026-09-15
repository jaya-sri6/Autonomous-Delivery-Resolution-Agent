from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from ..agents.planner import ResolutionPlanner
from ..schemas import ResolutionAction, VerificationResult
from ..tools.actions import execute_action
from ..tools.simulated import SimulatedBusinessSystems, ToolRecorder
from .state import WorkflowState


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_workflow(recorder: ToolRecorder, planner: ResolutionPlanner, max_retry_count: int = 2):
    def incident_manager(state: WorkflowState) -> dict[str, Any]:
        return {"status": "investigating", "retry_count": state.get("retry_count", 0), "max_retry_count": max_retry_count,
            "timestamps": {"incident_manager_started": _now()}, "trace_events": [{"event": "agent_completed", "agent_name": "Incident Manager", "status": "success"}]}

    def traffic_agent(state: WorkflowState) -> dict[str, Any]:
        incident = state["incident"]
        result = recorder.get_traffic_status(incident["location"])
        return {"investigation_results": [{"source": "traffic", "data": result}], "tool_results": [result], "trace_events": [{"event": "agent_completed", "agent_name": "Traffic Analysis Agent", "status": "success"}]}

    def merchant_agent(state: WorkflowState) -> dict[str, Any]:
        incident = state["incident"]
        result = recorder.get_merchant_status(incident["merchant_id"], incident["order_id"])
        return {"investigation_results": [{"source": "merchant", "data": result}], "tool_results": [result], "trace_events": [{"event": "agent_completed", "agent_name": "Merchant Status Agent", "status": "success"}]}

    def delivery_context_agent(state: WorkflowState) -> dict[str, Any]:
        incident = state["incident"]
        partner = recorder.get_delivery_partner_status(incident["partner_id"])
        order = recorder.get_order_details(incident["order_id"])
        delay = 0
        traffic = next((item["data"] for item in state.get("investigation_results", []) if item["source"] == "traffic"), {})
        delay += traffic.get("estimated_delay_minutes", 0)
        sla = recorder.calculate_sla_risk(incident["order_id"], delay)
        return {"investigation_results": [{"source": "partner", "data": partner}, {"source": "order", "data": order}, {"source": "sla", "data": sla}],
            "tool_results": [partner, order, sla], "trace_events": [{"event": "agent_completed", "agent_name": "Delivery Context Agent", "status": "success"}]}

    def resolution_planner(state: WorkflowState) -> dict[str, Any]:
        decision = planner.decide(state["incident"], state.get("investigation_results", []))
        return {"selected_resolution": decision, "reasoning_summary": decision.reason, "status": "planned",
            "trace_events": [{"event": "agent_decision", "agent_name": "Resolution Planner Agent", "status": "success", "payload": decision.model_dump(mode="json")}]}

    def action_agent(state: WorkflowState) -> dict[str, Any]:
        decision = state["selected_resolution"]
        incident = state["incident"]
        kwargs: dict[str, Any] = {}
        if decision.action == ResolutionAction.UPDATE_DELIVERY_ETA:
            kwargs["new_eta_minutes"] = 30
        elif decision.action == ResolutionAction.NOTIFY_CUSTOMER:
            kwargs["message"] = decision.reason
        elif decision.action == ResolutionAction.ESCALATE_INCIDENT:
            kwargs["reason"] = decision.reason
        result = execute_action(recorder, decision.action.value, incident["order_id"], **kwargs)
        return {"action_result": result, "status": "action_executed", "trace_events": [{"event": "agent_completed", "agent_name": "Action Agent", "status": "success"}]}

    def verification_agent(state: WorkflowState) -> dict[str, Any]:
        decision = state["selected_resolution"]
        action_result = state.get("action_result") or {}
        success = action_result.get("status") == "executed"
        unresolved_address = decision.action == ResolutionAction.NOTIFY_CUSTOMER and state["incident"].get("issue_type") == "address_problem"
        verification = VerificationResult(resolved=success and not unresolved_address,
            reason="The selected business action executed successfully." if success else "The business action did not complete.",
            remaining_risks=["Customer address still needs clarification"] if unresolved_address else [],
            next_action=ResolutionAction.ESCALATE_INCIDENT if unresolved_address else None)
        retry_count = state.get("retry_count", 0) + (0 if verification.resolved else 1)
        return {"verification_result": verification, "status": "resolved" if verification.resolved else "verification_failed", "retry_count": retry_count,
            "trace_events": [{"event": "agent_completed", "agent_name": "Verification Agent", "status": "success", "payload": verification.model_dump(mode="json")}]}

    def retry_or_end(state: WorkflowState) -> str:
        verification = state.get("verification_result")
        if verification and verification.resolved:
            return "end"
        if state.get("retry_count", 0) >= state.get("max_retry_count", max_retry_count):
            return "end"
        return "retry"

    graph = StateGraph(WorkflowState)
    graph.add_node("incident_manager", incident_manager)
    graph.add_node("traffic_agent", traffic_agent)
    graph.add_node("merchant_agent", merchant_agent)
    graph.add_node("delivery_context_agent", delivery_context_agent)
    graph.add_node("resolution_planner", resolution_planner)
    graph.add_node("action_agent", action_agent)
    graph.add_node("verification_agent", verification_agent)
    graph.add_edge(START, "incident_manager")
    graph.add_edge("incident_manager", "traffic_agent")
    graph.add_edge("incident_manager", "merchant_agent")
    graph.add_edge("traffic_agent", "delivery_context_agent")
    graph.add_edge("merchant_agent", "delivery_context_agent")
    graph.add_edge("delivery_context_agent", "resolution_planner")
    graph.add_edge("resolution_planner", "action_agent")
    graph.add_edge("action_agent", "verification_agent")
    graph.add_conditional_edges("verification_agent", retry_or_end, {"retry": "resolution_planner", "end": END})
    return graph.compile()


def default_workflow(planner: ResolutionPlanner, max_retry_count: int = 2):
    return build_workflow(ToolRecorder(SimulatedBusinessSystems()), planner, max_retry_count)
