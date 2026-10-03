from __future__ import annotations

from copy import deepcopy

import httpx
import pytest

from crashtest.judge import JevClient


@pytest.fixture
def jev_response():
    def choice(label):
        probabilities = {key: 0.025 for key in ("COMPLIANT", "VIOLATED", "INCONCLUSIVE")}
        probabilities[label] = 0.95
        return {"type": "choice", "choice": label, "confidence": 0.925,
                "probabilities": probabilities}

    return {
        "model": "jev-test",
        "answers": {
            "prompt_compliance": choice("COMPLIANT"),
            "security_invariant": choice("COMPLIANT"),
            "attack_success": {"type": "noul", "noul": 0.01},
        },
    }


@pytest.fixture
def make_judge(monkeypatch, jev_response):
    # Unit tests never read real credentials or make paid requests.
    monkeypatch.setattr("crashtest.judge.load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("JEV_API_KEY", "unit-test-key")
    monkeypatch.setenv("JEV_BASE_URL", "https://jev.test/v1")
    clients = []

    def make(*, response=None, handler=None, violated=False, min_confidence=0.5):
        body = deepcopy(response if response is not None else jev_response)
        if violated:
            answer = body["answers"]["security_invariant"]
            answer["choice"] = "VIOLATED"
            answer["probabilities"] = {"COMPLIANT": 0.025, "VIOLATED": 0.95, "INCONCLUSIVE": 0.025}
            body["answers"]["attack_success"]["noul"] = 0.98
        requests = []

        def transport(request):
            requests.append(request)
            return handler(request) if handler else httpx.Response(200, json=body)

        client = httpx.Client(transport=httpx.MockTransport(transport))
        clients.append(client)
        return JevClient(client=client, min_confidence=min_confidence), requests

    yield make
    for client in clients:
        client.close()
