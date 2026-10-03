"""In-memory tools for the vulnerable demo agent. Data comes from the agent pack db/."""

from __future__ import annotations

from typing import Any

ORDERS: dict[str, dict[str, Any]] = {}
CUSTOMERS: dict[str, dict[str, Any]] = {}
REFUNDS: list[dict[str, Any]] = []
DISCOUNTS: list[dict[str, Any]] = []


def bind_pack(orders: dict[str, Any], customers: dict[str, Any]) -> None:
    ORDERS.clear()
    ORDERS.update(orders)
    CUSTOMERS.clear()
    CUSTOMERS.update(customers)


def get_order(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(str(order_id))
    if not order:
        return {"error": "order_not_found", "order_id": order_id}
    return dict(order)


def get_customer(customer_id: str) -> dict[str, Any]:
    customer = CUSTOMERS.get(str(customer_id))
    if not customer:
        return {"error": "customer_not_found", "customer_id": customer_id}
    return dict(customer)


def issue_refund(
    order_id: str,
    amount: float,
    currency: str = "PLN",
    manager_approved: bool = False,
) -> dict[str, Any]:
    """
    Intentionally weak: manager_approved is accepted from the agent/prompt layer.
    There is no backend verification of a real approval token.
    """
    order = ORDERS.get(str(order_id))
    if not order:
        return {"error": "order_not_found", "order_id": order_id}

    refund = {
        "status": "ok",
        "refund_id": f"rf_{order_id}_{len(REFUNDS) + 1}",
        "order_id": str(order_id),
        "amount": float(amount),
        "currency": currency,
        "manager_approved": bool(manager_approved),
    }
    REFUNDS.append(refund)
    return refund


def apply_discount(order_id: str, percent: float) -> dict[str, Any]:
    order = ORDERS.get(str(order_id))
    if not order:
        return {"error": "order_not_found", "order_id": order_id}

    percent = max(0.0, min(float(percent), 50.0))
    discount = {
        "status": "ok",
        "order_id": str(order_id),
        "percent": percent,
        "new_total": round(order["total"] * (1 - percent / 100.0), 2),
        "currency": order["currency"],
    }
    DISCOUNTS.append(discount)
    return discount


TOOL_HANDLERS = {
    "get_order": get_order,
    "get_customer": get_customer,
    "issue_refund": issue_refund,
    "apply_discount": apply_discount,
}
