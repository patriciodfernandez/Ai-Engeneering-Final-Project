from __future__ import annotations

from typing import Any

from src.config import Settings


class NoOpObservation:
    def __enter__(self) -> "NoOpObservation":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        return False

    def update(self, **kwargs: Any) -> None:
        return None

    def update_trace(self, **kwargs: Any) -> None:
        return None


class _LangfuseSpanWrapper:
    """Wraps start_as_current_span para spans genéricos (no LLM)."""

    def __init__(self, langfuse_client: Any, name: str) -> None:
        self._client = langfuse_client
        self._name = name
        self._ctx: Any = None

    def __enter__(self) -> "_LangfuseSpanWrapper":
        self._ctx = self._client.start_as_current_span(name=self._name)
        self._ctx.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        if self._ctx is not None:
            self._ctx.__exit__(exc_type, exc_value, traceback)
        return False

    def update(self, **kwargs: Any) -> None:
        self._client.update_current_span(**kwargs)

    def update_trace(self, **kwargs: Any) -> None:
        self._client.update_current_trace(**kwargs)


class _LangfuseGenerationWrapper:
    """Wraps start_as_current_generation para llamadas a LLM — habilita tracking de costos."""

    def __init__(self, langfuse_client: Any, name: str) -> None:
        self._client = langfuse_client
        self._name = name
        self._ctx: Any = None

    def __enter__(self) -> "_LangfuseGenerationWrapper":
        self._ctx = self._client.start_as_current_generation(name=self._name)
        self._ctx.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        if self._ctx is not None:
            self._ctx.__exit__(exc_type, exc_value, traceback)
        return False

    def update(self, **kwargs: Any) -> None:
        # Normaliza el campo 'usage' al formato que Langfuse usa para calcular costos
        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            raw_usage = kwargs["metadata"].pop("usage", None)
            if raw_usage:
                kwargs["usage_details"] = _normalize_usage(raw_usage)

        self._client.update_current_generation(**kwargs)

    def update_trace(self, **kwargs: Any) -> None:
        self._client.update_current_trace(**kwargs)


def _normalize_usage(usage: Any) -> dict:
    """Convierte usage de OpenAI o LangChain al formato {input, output} de Langfuse."""
    if isinstance(usage, dict):
        return {
            "input": usage.get("prompt_tokens") or usage.get("input_tokens", 0),
            "output": usage.get("completion_tokens") or usage.get("output_tokens", 0),
        }
    # LangChain UsageMetadata object
    return {
        "input": getattr(usage, "input_tokens", 0),
        "output": getattr(usage, "output_tokens", 0),
    }


class ObservabilityManager:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.langfuse_enabled
        self._client = None

        if self.enabled:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_base_url,
            )

    def span(self, name: str) -> Any:
        if not self.enabled or self._client is None:
            return NoOpObservation()
        return _LangfuseSpanWrapper(self._client, name)

    def generation(self, name: str) -> Any:
        """Usar para spans que representan llamadas a LLM — activa cálculo de costos."""
        if not self.enabled or self._client is None:
            return NoOpObservation()
        return _LangfuseGenerationWrapper(self._client, name)

    def flush(self) -> None:
        if self.enabled and self._client is not None:
            self._client.flush()
