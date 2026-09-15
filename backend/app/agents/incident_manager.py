from typing import Any


def investigation_plan(incident: dict[str, Any]) -> list[str]:
    """Return the specialist domains required for an incident."""
    return ["traffic", "merchant", "delivery_context"]
