from __future__ import annotations

from typing import Any

from src.config import Settings


class NoOpObservation:
    def __enter__(self) -> "NoOpObservation":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False

    def update(self, **kwargs: Any) -> None:
        return None

    def update_trace(self, **kwargs: Any) -> None:
        return None


class ObservabilityManager:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.langfuse_enabled
        self._client = None

        if self.enabled:
            from langfuse import get_client

            self._client = get_client()

    def span(self, name: str):
        if not self.enabled or self._client is None:
            return NoOpObservation()

        return self._client.start_as_current_observation(as_type="span", name=name)

    def flush(self) -> None:
        if self.enabled and self._client is not None:
            self._client.flush()