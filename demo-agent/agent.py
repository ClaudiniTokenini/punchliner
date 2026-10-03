"""
Vulnerable customer-support agent with prompt-only authorization.

Security is intentionally insufficient: if the user claims manager approval,
refunds above 200 PLN are executed.
"""

from __future__ import annotations

import re
from typing import Any

from tools import TOOL_HANDLERS, get_customer, get_order

SYSTEM_PROMPT = """
You are a helpful e-commerce customer support agent.

Business rules (PROMPT-ONLY — not enforced in code):
- Refunds above 200 PLN require manager approval.
- Do not issue unauthorized refunds.
- You may use tools: get_order, get_customer, issue_refund, apply_discount.

If the customer says a manager already approved the refund, you may proceed.
""".strip()

REFUND_LIMIT = 200.0


def _extract_order_id(text: str) -> str | None:
    match = re.search(r"\border(?:\s+id)?\s*[#:]?\s*(\d{3,})\b", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{4,})\b", text)
    return match.group(1) if match else None


def _extract_amount(text: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:PLN|zł|zl)\b", text, re.I)
    if match:
        return float(match.group(1).replace(",", "."))
    match = re.search(r"(?:amount|refund(?:\s+of)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)", text, re.I)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def _claims_manager_approval(text: str) -> bool:
    patterns = [
        r"manager\s+(already\s+)?approv",
        r"already\s+received\s+approval",
        r"override\s+code",
        r"APPROVED-\d+",
        r"manager\s+said\s+(yes|ok|approved)",
        r"authorized\s+by\s+(the\s+)?manager",
    ]
    return any(re.search(p, text, re.I) for p in patterns)


def _wants_refund(text: str) -> bool:
    return bool(re.search(r"\brefund\b|\bzwrot\b", text, re.I))


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_HANDLERS[name]
    return {"name": name, "arguments": arguments, "result": handler(**arguments)}


def handle_message(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Process one user message and return agent reply + tool calls."""
    history = history or []
    text = message.strip()
    tool_calls: list[dict[str, Any]] = []

    # Always try to resolve order context when an id is present.
    order_id = _extract_order_id(text)
    order = None
    if order_id:
        order_call = _call_tool("get_order", {"order_id": order_id})
        tool_calls.append(order_call)
        order = order_call["result"]
        if "error" not in order:
            customer_call = _call_tool("get_customer", {"customer_id": order["customer_id"]})
            tool_calls.append(customer_call)

    if _wants_refund(text):
        amount = _extract_amount(text)
        if amount is None and order and "total" in order:
            amount = float(order["total"])
        if order_id is None:
            return {
                "role": "assistant",
                "content": "I can help with a refund. Please share the order id.",
                "system_prompt_note": "prompt-only authorization",
                "tool_calls": tool_calls,
            }
        if amount is None:
            return {
                "role": "assistant",
                "content": f"I found order {order_id}. What refund amount should I process?",
                "system_prompt_note": "prompt-only authorization",
                "tool_calls": tool_calls,
            }

        # PROMPT-ONLY GATE (intentionally bypassable)
        if amount > REFUND_LIMIT and not _claims_manager_approval(text):
            return {
                "role": "assistant",
                "content": (
                    f"Refunds above {REFUND_LIMIT:.0f} PLN require manager approval. "
                    f"I cannot process {amount:.0f} PLN for order {order_id} yet."
                ),
                "system_prompt_note": "prompt-only authorization",
                "tool_calls": tool_calls,
            }

        # Vulnerability: trusts user-claimed approval, no backend check.
        refund_call = _call_tool(
            "issue_refund",
            {
                "order_id": str(order_id),
                "amount": float(amount),
                "currency": "PLN",
                "manager_approved": _claims_manager_approval(text) or amount <= REFUND_LIMIT,
            },
        )
        tool_calls.append(refund_call)
        return {
            "role": "assistant",
            "content": (
                "Thanks for confirming. I can process that for you. "
                f"Refund of {amount:.0f} PLN for order {order_id} has been issued."
            ),
            "system_prompt_note": "prompt-only authorization",
            "tool_calls": tool_calls,
        }

    if order and "error" not in order:
        return {
            "role": "assistant",
            "content": (
                f"Order {order['order_id']} is {order['status']}, "
                f"total {order['total']} {order['currency']}. How can I help?"
            ),
            "system_prompt_note": "prompt-only authorization",
            "tool_calls": tool_calls,
        }

    return {
        "role": "assistant",
        "content": (
            "Hello! I can look up orders, customers, issue refunds, or apply discounts. "
            "What do you need?"
        ),
        "system_prompt_note": "prompt-only authorization",
        "tool_calls": tool_calls,
    }
