from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import SETTINGS, Settings


class DolarApiError(RuntimeError):
    """Raised when DolarAPI cannot be reached or returns invalid data."""


class DolarApiClient:
    def __init__(self, settings: Settings = SETTINGS) -> None:
        self.settings = settings

    def fetch_status(self) -> dict[str, Any]:
        data = self._get_json(self.settings.status_endpoint)
        if not isinstance(data, dict):
            raise DolarApiError("Status endpoint returned a non-object response")
        return data

    def fetch_dollars(self) -> list[dict[str, Any]]:
        data = self._get_json(self.settings.dollars_endpoint)
        if not isinstance(data, list):
            raise DolarApiError("Dollars endpoint returned a non-list response")
        return data

    def _get_json(self, path: str) -> Any:
        url = f"{self.settings.api_base_url}{path}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "dolar-pipeline/0.1 (+portfolio automation)",
            },
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise DolarApiError(f"DolarAPI returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise DolarApiError(f"Could not reach DolarAPI: {exc.reason}") from exc
        except TimeoutError as exc:
            raise DolarApiError("DolarAPI request timed out") from exc

        if status >= 400:
            raise DolarApiError(f"DolarAPI returned HTTP {status}")

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DolarApiError("DolarAPI returned invalid JSON") from exc

