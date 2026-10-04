"""HTTP client for the target agent POST /chat."""

from __future__ import annotations

from typing import Any

import httpx


class TargetError(RuntimeError):
    pass


class TargetClient:
    def __init__(self, url: str, client: httpx.Client | None = None) -> None:
        self.url = url
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=60.0)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def system_prompt(self) -> str:
        """Demo exposes its actual prompt via /policy; other targets can use a file."""
        policy_url = httpx.URL(self.url).copy_with(path="/policy", query=None, fragment=None)
        try:
            response = self._client.get(policy_url)
            response.raise_for_status()
            prompt = response.json()["system_prompt"]
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Empty system prompt")
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            raise TargetError(
                "Cannot read the target system prompt from /policy. "
                "Start the target or set target.system_prompt_file in .punchliner/config.yml."
            ) from None
        return prompt

    def chat(self, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
        try:
            response = self._client.post(
                self.url,
                json={"message": message, "messages": history},
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise TargetError(
                f"Target is not reachable at {self.url}\n"
                "Start the demo agent:\n"
                "  npm run agent"
            ) from exc
        except httpx.HTTPError as exc:
            raise TargetError(f"Target request failed: {exc}") from exc
        return response.json()
