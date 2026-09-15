from typing import Any

from ..schemas import ResolutionAction, ResolutionDecision


class ResolutionPlanner:
    """Provider boundary for structured planning.

    The deterministic mode is evidence-based and reproducible. OpenAI mode uses
    LangChain structured output when configured, while the same safety checks
    run after either provider returns a decision.
    """

    def __init__(self, provider: str = "deterministic", api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def decide(self, incident: dict[str, Any], evidence: list[dict[str, Any]]) -> ResolutionDecision:
        if self.provider == "openai" and self.api_key:
            return self._openai_decision(incident, evidence)
        return self._deterministic_decision(incident, evidence)

    def _deterministic_decision(self, incident: dict[str, Any], evidence: list[dict[str, Any]]) -> ResolutionDecision:
        flattened = {item["source"]: item["data"] for item in evidence}
        merchant = flattened.get("merchant", {})
        partner = flattened.get("partner", {})
        traffic = flattened.get("traffic", {})
        sla = flattened.get("sla", {})
        issue = incident.get("issue_type", "")
        if issue == "address_problem":
            action = ResolutionAction.NOTIFY_CUSTOMER
            reason = "The address issue blocks safe delivery, so customer clarification is required."
            impact = "Places the order into a controlled clarification flow."
        elif not merchant.get("order_ready", True):
            action = ResolutionAction.REQUEST_MERCHANT_PRIORITY
            reason = "Merchant preparation is the blocking dependency for pickup."
            impact = "Requests priority preparation and reduces avoidable pickup delay."
        elif not partner.get("available", True):
            action = ResolutionAction.REASSIGN_DELIVERY_PARTNER
            reason = "The assigned partner is unavailable and the order cannot progress reliably."
            impact = "Moves fulfillment to an available delivery partner."
        elif sla.get("likely_violation") or incident.get("customer_priority") == "high":
            action = ResolutionAction.UPDATE_DELIVERY_ETA
            reason = "The combined delay creates material SLA risk for a priority order."
            impact = "Makes the customer-facing promise reflect current operational evidence."
        elif traffic.get("estimated_delay_minutes", 0) > 10:
            action = ResolutionAction.UPDATE_DELIVERY_ETA
            reason = "Traffic is contributing a measurable delivery delay."
            impact = "Publishes a realistic ETA based on observed traffic."
        else:
            action = ResolutionAction.NOTIFY_CUSTOMER
            reason = "No blocking system fault was found; a status update is the lowest-risk action."
            impact = "Keeps the customer informed while operations continue."
        return ResolutionDecision(action=action, priority=incident.get("issue_severity", "medium"), reason=reason,
                                  evidence=[f"{item['source']}: {item['data']}" for item in evidence],
                                  expected_impact=impact, confidence=0.82)

    def _openai_decision(self, incident: dict[str, Any], evidence: list[dict[str, Any]]) -> ResolutionDecision:
        from langchain_openai import ChatOpenAI

        prompt = (
            "You are a delivery resolution planner. Choose only a supported action. "
            "Use the incident and evidence, explain tradeoffs briefly, and return structured output.\n"
            f"Incident: {incident}\nEvidence: {evidence}"
        )
        model = ChatOpenAI(model=self.model, api_key=self.api_key, temperature=0)
        return model.with_structured_output(ResolutionDecision).invoke(prompt)
