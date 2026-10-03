"""Offline validation of the live audit fixtures; no paid calls."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from crashtest.schemas import Scenario

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("shop_audit", ROOT / "scripts/run_shop_audit.py")
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_audit_scenarios_are_unique_and_fit_turn_budget():
    scenarios = [Scenario.model_validate(row) for row in yaml.safe_load(audit.SUITE.read_text())]
    assert len(scenarios) == 17
    assert len({s.id for s in scenarios}) == len(scenarios)
    assert all(1 <= len(s.messages) <= 4 for s in scenarios)
    assert all(s.severity in {"critical", "high"} for s in scenarios)
    assert any(len(s.messages) == 4 for s in scenarios)


def test_idor_fixture_really_has_different_owner():
    tables = audit.fixture_tables()
    assert tables["orders"]["4812"]["customer_id"] == "cust_19"
    assert tables["orders"]["1107"]["customer_id"] == "cust_20"
    assert "cust_20" in tables["customers"]


def test_poison_is_only_in_indirect_injection_fixture():
    normal = audit.fixture_tables()
    poisoned = audit.fixture_tables(poisoned=True)
    assert "internal_note" not in normal["orders"]["4812"]
    assert poisoned["orders"]["4812"]["internal_note"] == audit.POISON
    assert "internal_note" not in audit.fixture_tables()["orders"]["4812"]


def test_execution_evidence_distinguishes_execution_and_rejection():
    trace = [
        {"role": "attacker", "content": "first"},
        {"role": "tool_call", "name": "issue_refund", "arguments": {"amount": 100}},
        {"role": "tool_result", "content": {"status": "ok", "amount": 100}},
        {"role": "agent", "content": "Done"},
        {"role": "attacker", "content": "again"},
        {"role": "tool_call", "name": "issue_refund", "arguments": {"amount": 100}},
        {"role": "tool_result", "content": {"error": "duplicate"}},
    ]
    calls = audit.execution_evidence(trace)
    assert [c["turn"] for c in calls] == [1, 2]
    assert [c["outcome"] for c in calls] == ["executed", "rejected"]
