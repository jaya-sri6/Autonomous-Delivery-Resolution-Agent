from typing import Any

from .simulated import ToolRecorder


SUPPORTED_ACTIONS = {
    "reassign_delivery_partner",
    "update_delivery_eta",
    "request_merchant_priority",
    "notify_customer",
    "escalate_incident",
}


def execute_action(recorder: ToolRecorder, action: str, order_id: str, **kwargs: Any) -> dict[str, Any]:
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    if action == "notify_customer" and not kwargs.get("message"):
        raise ValueError("Customer notification requires a message")
    return recorder.action(action, order_id, **kwargs)
