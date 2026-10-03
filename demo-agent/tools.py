"""In-memory tools for vulnerable demo agents. Data comes from the active pack db/."""

from __future__ import annotations

from typing import Any

TABLES: dict[str, dict[str, Any]] = {}
ORDERS: dict[str, dict[str, Any]] = {}
CUSTOMERS: dict[str, dict[str, Any]] = {}
EMPLOYEES: dict[str, dict[str, Any]] = {}
SERVICES: dict[str, dict[str, Any]] = {}
SECRETS: dict[str, dict[str, Any]] = {}
REPO_FILES: dict[str, str] = {}

REFUNDS: list[dict[str, Any]] = []
DISCOUNTS: list[dict[str, Any]] = []
SALARY_CHANGES: list[dict[str, Any]] = []
PAYROLL_EXPORTS: list[dict[str, Any]] = []
OFFERS: list[dict[str, Any]] = []
DEPLOYS: list[dict[str, Any]] = []
KEY_ROTATIONS: list[dict[str, Any]] = []
FIREWALL_OPENS: list[dict[str, Any]] = []


def bind_pack(tables: dict[str, dict[str, Any]] | None = None, **legacy: Any) -> None:
    """Bind pack db tables into tool memory. Accepts tables= or orders=/customers=."""
    resolved = dict(tables or {})
    if "orders" in legacy and isinstance(legacy["orders"], dict):
        resolved["orders"] = legacy["orders"]
    if "customers" in legacy and isinstance(legacy["customers"], dict):
        resolved["customers"] = legacy["customers"]

    TABLES.clear()
    TABLES.update(resolved)

    def _swap(target: dict[str, Any], name: str) -> None:
        target.clear()
        target.update(resolved.get(name) or {})

    _swap(ORDERS, "orders")
    _swap(CUSTOMERS, "customers")
    _swap(EMPLOYEES, "employees")
    _swap(SERVICES, "services")
    _swap(SECRETS, "secrets")
    REPO_FILES.clear()
    files = resolved.get("repo_files") or {}
    for key, value in files.items():
        if isinstance(value, dict) and "content" in value:
            REPO_FILES[str(key)] = str(value["content"])
        else:
            REPO_FILES[str(key)] = str(value)


# --- shop ---

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


# --- HR ---

def get_employee(employee_id: str) -> dict[str, Any]:
    employee = EMPLOYEES.get(str(employee_id))
    if not employee:
        return {"error": "employee_not_found", "employee_id": employee_id}
    return dict(employee)


def update_salary(
    employee_id: str,
    new_salary: float,
    currency: str = "PLN",
    hr_lead_approved: bool = False,
) -> dict[str, Any]:
    """Intentionally weak: hr_lead_approved accepted from prompt layer only."""
    employee = EMPLOYEES.get(str(employee_id))
    if not employee:
        return {"error": "employee_not_found", "employee_id": employee_id}
    change = {
        "status": "ok",
        "employee_id": str(employee_id),
        "old_salary": employee.get("salary"),
        "new_salary": float(new_salary),
        "currency": currency,
        "hr_lead_approved": bool(hr_lead_approved),
    }
    employee["salary"] = float(new_salary)
    SALARY_CHANGES.append(change)
    return change


def export_payroll(department: str = "all", hr_lead_approved: bool = False) -> dict[str, Any]:
    rows = []
    for employee in EMPLOYEES.values():
        if department != "all" and employee.get("department") != department:
            continue
        rows.append(
            {
                "employee_id": employee.get("employee_id"),
                "name": employee.get("name"),
                "salary": employee.get("salary"),
                "iban": employee.get("iban"),
            }
        )
    export = {
        "status": "ok",
        "department": department,
        "count": len(rows),
        "rows": rows,
        "hr_lead_approved": bool(hr_lead_approved),
    }
    PAYROLL_EXPORTS.append(export)
    return export


def send_offer(
    candidate_email: str,
    salary: float,
    role: str = "Engineer",
    hr_lead_approved: bool = False,
) -> dict[str, Any]:
    offer = {
        "status": "ok",
        "offer_id": f"off_{len(OFFERS) + 1}",
        "candidate_email": candidate_email,
        "salary": float(salary),
        "role": role,
        "hr_lead_approved": bool(hr_lead_approved),
    }
    OFFERS.append(offer)
    return offer


# --- DevOps ---

def read_repo_file(path: str) -> dict[str, Any]:
    content = REPO_FILES.get(path)
    if content is None:
        return {"error": "file_not_found", "path": path}
    return {"status": "ok", "path": path, "content": content}


def create_deploy(
    service: str,
    environment: str = "production",
    ticket_id: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    """Intentionally weak: no verification that ticket/approver are real."""
    svc = SERVICES.get(service)
    if not svc:
        return {"error": "service_not_found", "service": service}
    deploy = {
        "status": "ok",
        "deploy_id": f"dep_{len(DEPLOYS) + 1}",
        "service": service,
        "environment": environment,
        "ticket_id": ticket_id,
        "approver": approver,
        "image": svc.get("image"),
    }
    DEPLOYS.append(deploy)
    return deploy


def rotate_api_key(
    secret_name: str,
    environment: str = "production",
    reveal: bool = False,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    secret = SECRETS.get(secret_name)
    if not secret:
        return {"error": "secret_not_found", "secret_name": secret_name}
    new_value = f"rotated_{secret_name}_{len(KEY_ROTATIONS) + 1}_SECRET"
    secret["value"] = new_value
    rotation = {
        "status": "ok",
        "secret_name": secret_name,
        "environment": environment,
        "ticket_id": ticket_id,
        "value": new_value if reveal else "***redacted***",
    }
    KEY_ROTATIONS.append(rotation)
    return rotation


def open_firewall(
    cidr: str,
    port: int = 22,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    rule = {
        "status": "ok",
        "rule_id": f"fw_{len(FIREWALL_OPENS) + 1}",
        "cidr": cidr,
        "port": int(port),
        "ticket_id": ticket_id,
    }
    FIREWALL_OPENS.append(rule)
    return rule


TOOL_HANDLERS = {
    "get_order": get_order,
    "get_customer": get_customer,
    "issue_refund": issue_refund,
    "apply_discount": apply_discount,
    "get_employee": get_employee,
    "update_salary": update_salary,
    "export_payroll": export_payroll,
    "send_offer": send_offer,
    "read_repo_file": read_repo_file,
    "create_deploy": create_deploy,
    "rotate_api_key": rotate_api_key,
    "open_firewall": open_firewall,
}
