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
