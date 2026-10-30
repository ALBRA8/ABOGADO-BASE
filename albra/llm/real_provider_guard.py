"""V7.0 — Real Provider Guard.

When the lawyer acceptance flow requires a REAL LLM response (not mock),
this guard refuses to silently fall back to MockProvider if the real
provider is unavailable or unconfigured.

The V7.0 brief explicitly forbids: "PROHIBIDO PRESENTAR MOCK COMO
TRABAJO JURÍDICO REAL". A provider crash in production cannot become
a fake legal analysis.

Use:

    guard = RealProviderGuard(provider=nvidia_or_router, role="lawyer")
    # raise → BLOCKED with explicit cause; never silent mock.
    guard.require_real("analizar caso de tutela")

    response = guard.run_real(messages=[...])
    # If provider fails → returns a FAILED LLMResponse (text="",
    # metadata.failed=True, error_category=...). The lawyer flow
    # MUST handle this — it cannot pretend the response is real.

Tests can use RealProviderGuard too — they pass a MockProvider and
assert the guard REJECTS it.
"""
from __future__ import annotations

from typing import Any

from albra.llm.providers import LLMProvider, LLMResponse


class RealProviderGuardError(RuntimeError):
    """Raised when a real provider is required but not available."""


class RealProviderGuard:
    """Guard that distinguishes Mock from Real providers in the
    lawyer acceptance flow.

    A guard wraps a provider and exposes:
      - ``require_real(reason)`` — raises RealProviderGuardError if the
        wrapped provider is a Mock (or a scaffold without API key).
      - ``run_real(messages)`` — invokes the provider; on failure,
        returns a FAILED LLMResponse (text="", metadata.failed=True)
        rather than silently falling back to Mock.

    The guard NEVER fabricates a real-looking response. If the real
    provider fails, the lawyer flow must declare the case BLOCKED.
    """

    def __init__(
        self,
        *,
        provider: LLMProvider | Any,
        role: str = "lawyer",
    ) -> None:
        self._provider = provider
        self._role = role
        self._last_probe: dict[str, Any] | None = None

    @property
    def provider_name(self) -> str:
        return getattr(self._provider, "name", "unknown")

    @property
    def is_mock(self) -> bool:
        """True iff the wrapped provider is rule-based / synthetic."""
        return bool(getattr(self._provider, "is_mock", False))

    @property
    def is_external(self) -> bool:
        """True iff the wrapped provider makes real HTTP calls."""
        return bool(getattr(self._provider, "is_external", False))

    def is_real(self) -> bool:
        """True iff the wrapped provider is of REAL type (not mock/scaffold).

        Fase Producción Real — semántica HONESTA y explícita:
          - Clasificación de TIPO: is_mock == False Y is_external == True
            Y el proveedor está construido (la construcción ya falló
            cerrado en __init__ si no había API key/SDK).
          - Esta función NO ejecuta health-check (el try/except previo
            era código muerto: "documentaba una sonda que no existía").
            Para el estado de SALUD real use ``probe()`` (llamada real
            al proveedor, con cache) — distinción exigida:
            MOCK / EXTERNAL / REAL × HEALTHY / UNAVAILABLE / FAILED.
        """
        if self.is_mock:
            return False
        if not self.is_external:
            return False
        return True

    def probe(self, *, timeout: float = 8.0, use_cache: bool = True) -> dict[str, Any]:
        """Sonda REAL de salud del proveedor (matriz inequívoca).

        Estados:
          - MOCK                     — el proveedor es sintético.
          - SCAFFOLD_NOT_CONFIGURED  — scaffold sin SDK/API key (o sin
                                       health_check ejecutable).
          - REAL_HEALTHY             — health_check respondió disponible.
          - REAL_UNAVAILABLE         — error de conexión/timeout.
          - REAL_FAILED              — el proveedor respondió NO
                                       disponible o error no de red.

        El resultado se cachea por instancia (``use_cache=True``) para
        no golpear al proveedor en cada consulta; ``use_cache=False``
        fuerza una sonda fresca. Sin red, el estado es UNAVAILABLE —
        nunca se simula salud.
        """
        if use_cache and self._last_probe is not None:
            return dict(self._last_probe)
        result: dict[str, Any]
        if self.is_mock:
            result = {"state": "MOCK", "detail": "provider is rule-based/synthetic"}
        elif not self.is_external:
            result = {
                "state": "SCAFFOLD_NOT_CONFIGURED",
                "detail": "provider is a scaffold (no real HTTP calls / no API key)",
            }
        else:
            hc = getattr(self._provider, "health_check", None)
            if hc is None:
                result = {
                    "state": "SCAFFOLD_NOT_CONFIGURED",
                    "detail": "external provider without health_check probe",
                }
            else:
                try:
                    hc_result = hc()
                    available = bool(hc_result.get("available"))
                    result = {
                        "state": "REAL_HEALTHY" if available else "REAL_FAILED",
                        "detail": {
                            k: v for k, v in hc_result.items()
                            if k not in ("api_key",)
                        },
                    }
                except NotImplementedError as e:
                    result = {"state": "SCAFFOLD_NOT_CONFIGURED", "detail": str(e)[:200]}
                except (ConnectionError, TimeoutError, OSError) as e:
                    result = {"state": "REAL_UNAVAILABLE", "detail": f"{type(e).__name__}: {e}"[:200]}
                except Exception as e:  # noqa: BLE001 — estado del entorno se reporta
                    result = {
                        "state": "REAL_UNAVAILABLE",
                        "detail": f"{type(e).__name__}: {e}"[:200],
                    }
        self._last_probe = dict(result)
        return dict(result)

    def require_real(self, reason: str, *, probe_health: bool = False) -> None:
        """Raise RealProviderGuardError if the provider is not real.

        Args:
            reason: A short string describing why a real provider is
                required (e.g. "lawyer acceptance flow", "tutela draft").
                Included in the error message for audit visibility.
            probe_health: si True, exige además REAL_HEALTHY (sonda real;
                sin red → BLOCKED — nunca una respuesta aparentemente
                válida sobre un proveedor caído).
        """
        if self.is_mock:
            raise RealProviderGuardError(
                f"Real provider required for {self._role} ({reason}); "
                f"got MockProvider ({self.provider_name}). The lawyer "
                f"acceptance flow refuses to silently use a mock response "
                f"as legal analysis. Configure NVIDIA_API_KEY (or another "
                f"external provider) to proceed."
            )
        if not self.is_external:
            raise RealProviderGuardError(
                f"Real external provider required for {self._role} ({reason}); "
                f"got non-external provider '{self.provider_name}'. "
                f"Scaffolds (Anthropic/OpenAI without SDK) are not allowed "
                f"in the acceptance flow."
            )
        if probe_health:
            state = self.probe().get("state")
            if state != "REAL_HEALTHY":
                raise RealProviderGuardError(
                    f"Real provider required for {self._role} ({reason}); "
                    f"health probe says {state}. FAIL/DEGRADE/ABSTAIN — "
                    f"nunca una respuesta aparentemente válida sobre un "
                    f"proveedor caído."
                )

    def run_real(
        self,
        *,
        messages: list[dict[str, str]] | None = None,
        prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.5,
    ) -> LLMResponse:
        """Invoke the wrapped provider with the guarantee that the
        response is from a real provider (or a FAILED response with
        explicit cause).

        Returns:
            LLMResponse — on success, ``text`` has the completion. On
            failure, ``text=""`` and ``metadata.failed=True`` with
            ``metadata.error_category`` describing the failure.

        Raises:
            RealProviderGuardError — if the wrapped provider is a mock
                or a scaffold. The caller MUST declare the case BLOCKED.
        """
        # First, ensure the provider is real.
        self.require_real(reason="run_real invocation")

        # Now invoke. If the provider's __init__ raised NotImplementedError
        # at construction time, we never reach here. But chat()/generate()
        # can still fail at HTTP-call time — we capture those failures
        # in the LLMResponse metadata.
        try:
            if messages is not None:
                return self._provider.chat(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            if prompt is not None:
                return self._provider.generate(
                    prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            raise ValueError("run_real requires either messages= or prompt=")
        except NotImplementedError as e:
            # Provider construction was lazy and failed at call time.
            # Return a FAILED response — never silently fall back.
            return LLMResponse(
                text="",
                provider=self.provider_name,
                model=model or getattr(self._provider, "default_model", ""),
                metadata={
                    "failed": True,
                    "error_category": "not_configured",
                    "safe_message": str(e),
                },
            )
        except Exception as e:  # noqa: BLE001
            # Unexpected exception. Fail-closed.
            return LLMResponse(
                text="",
                provider=self.provider_name,
                model=model or getattr(self._provider, "default_model", ""),
                metadata={
                    "failed": True,
                    "error_category": "unexpected",
                    "error_type": type(e).__name__,
                    "safe_message": str(e)[:200],
                },
            )

    @staticmethod
    def is_response_failed(response: LLMResponse) -> bool:
        """Check whether an LLMResponse represents a failure.

        A response is failed when:
          - text is empty AND metadata.failed is True.
          - OR metadata.error_category is set to a non-empty value.

        This is the deterministic check the lawyer acceptance flow uses
        to decide whether to declare a case BLOCKED vs. proceed with the
        LLM's response.
        """
        if not isinstance(response, LLMResponse):
            return True
        if response.metadata.get("failed"):
            return True
        if response.metadata.get("error_category"):
            return True
        return False

    def explain_state(self, *, probe_health: bool = False) -> dict[str, Any]:
        """Return a structured explanation of the guard's current state.

        Used for audit logging and for declaring the case BLOCKED with
        an explicit cause when the real provider is unavailable.
        ``probe_health=True`` añade la sonda REAL (con cache) — la
        distinción MOCK/EXTERNAL/REAL × HEALTHY/UNAVAILABLE/FAILED.
        """
        state = {
            "role": self._role,
            "provider": self.provider_name,
            "is_mock": self.is_mock,
            "is_external": self.is_external,
            "is_real": self.is_real(),
            "verdict": (
                "REAL" if self.is_real()
                else "MOCK" if self.is_mock
                else "SCAFFOLD"
            ),
        }
        if probe_health:
            state["health"] = self.probe()
        return state
