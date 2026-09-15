import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from langchain_core.tools import StructuredTool


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "business_systems.json"


class ToolExecutionError(RuntimeError):
    pass


class SimulatedBusinessSystems:
    def __init__(self, data_path: Path = DATA_PATH):
        with data_path.open(encoding="utf-8") as file:
            self.data = json.load(file)

    def traffic(self, location: str) -> dict[str, Any]:
        try:
            return self.data["traffic"][location]
        except KeyError as exc:
            raise ToolExecutionError(f"No traffic record for location: {location}") from exc

    def merchant(self, merchant_id: str, order_id: str) -> dict[str, Any]:
        try:
            result = dict(self.data["merchants"][merchant_id])
            result["order_id"] = order_id
            return result
        except KeyError as exc:
            raise ToolExecutionError(f"No merchant record for: {merchant_id}") from exc

    def partner(self, partner_id: str) -> dict[str, Any]:
        try:
            return self.data["partners"][partner_id]
        except KeyError as exc:
            raise ToolExecutionError(f"No partner record for: {partner_id}") from exc

    def order(self, order_id: str) -> dict[str, Any]:
        try:
            result = dict(self.data["orders"][order_id])
            result["order_id"] = order_id
            return result
        except KeyError as exc:
            raise ToolExecutionError(f"No order record for: {order_id}") from exc

    def sla_risk(self, order_id: str, estimated_delay: int) -> dict[str, Any]:
        order = self.order(order_id)
        minutes_until_sla = order["promised_delivery_minutes"] - estimated_delay
        likely_violation = minutes_until_sla <= 0
        risk_level = "critical" if likely_violation else "high" if minutes_until_sla <= 10 else "low"
        return {"risk_level": risk_level, "minutes_until_sla": minutes_until_sla, "likely_violation": likely_violation}


class ToolRecorder:
    def __init__(self, systems: SimulatedBusinessSystems, callback: Callable[..., None] | None = None):
        self.systems = systems
        self.callback = callback
        self.calls: list[dict[str, Any]] = []

    def _run(self, name: str, inputs: dict[str, Any], operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        started = time.perf_counter()
        timestamp = datetime.now(timezone.utc)
        try:
            output = operation()
            record = {"tool_name": name, "input": inputs, "output": output, "success": True, "error": None,
                      "timestamp": timestamp.isoformat(), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
        except Exception as exc:
            record = {"tool_name": name, "input": inputs, "output": {}, "success": False, "error": str(exc),
                      "timestamp": timestamp.isoformat(), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
            self.calls.append(record)
            if self.callback:
                self.callback(record)
            raise
        self.calls.append(record)
        if self.callback:
            self.callback(record)
        return output

    def get_traffic_status(self, location: str) -> dict[str, Any]:
        return self._run("get_traffic_status", {"location": location}, lambda: self.systems.traffic(location))

    def get_merchant_status(self, merchant_id: str, order_id: str) -> dict[str, Any]:
        return self._run("get_merchant_status", {"merchant_id": merchant_id, "order_id": order_id}, lambda: self.systems.merchant(merchant_id, order_id))

    def get_delivery_partner_status(self, partner_id: str) -> dict[str, Any]:
        return self._run("get_delivery_partner_status", {"partner_id": partner_id}, lambda: self.systems.partner(partner_id))

    def get_order_details(self, order_id: str) -> dict[str, Any]:
        return self._run("get_order_details", {"order_id": order_id}, lambda: self.systems.order(order_id))

    def calculate_sla_risk(self, order_id: str, estimated_delay: int) -> dict[str, Any]:
        return self._run("calculate_sla_risk", {"order_id": order_id, "estimated_delay": estimated_delay}, lambda: self.systems.sla_risk(order_id, estimated_delay))

    def action(self, name: str, order_id: str, **kwargs: Any) -> dict[str, Any]:
        if not order_id:
            raise ToolExecutionError("order_id is required for every business action")
        details = {"order_id": order_id, **kwargs}
        return self._run(name, details, lambda: {"action": name, "order_id": order_id, "status": "executed", **kwargs})

    def langchain_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(self.get_traffic_status),
            StructuredTool.from_function(self.get_merchant_status),
            StructuredTool.from_function(self.get_delivery_partner_status),
            StructuredTool.from_function(self.get_order_details),
            StructuredTool.from_function(self.calculate_sla_risk),
        ]
