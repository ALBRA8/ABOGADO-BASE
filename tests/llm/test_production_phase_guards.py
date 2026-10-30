"""Tests FASE 3 (niveles de retrieval) y FASE 4 (RealProviderGuard real).

FASE 3: BOOTSTRAP nunca se presenta como PRODUCTION; la fábrica falla
cerrado para el nivel persistente no implementado.

FASE 4: la sonda de salud del guard es REAL (matriz MOCK / EXTERNAL /
REAL × HEALTHY / UNAVAILABLE / FAILED); el try/except muerto que
"documentaba una sonda inexistente" está corregido; el router alcanza
al proveedor real (nvidia).
"""
from __future__ import annotations

import pytest

from albra.knowledge.retrieval_providers import (
    InMemoryRetrievalProvider,
    RetrievalTier,
    create_retrieval_provider,
)
from albra.llm.providers import LLMResponse, MockProvider
from albra.llm.real_provider_guard import (
    RealProviderGuard,
    RealProviderGuardError,
)

# ===== FASE 3: Retrieval tiers =====

def test_inmemory_es_bootstrap_nunca_production():
    assert InMemoryRetrievalProvider.tier == RetrievalTier.BOOTSTRAP
    p = InMemoryRetrievalProvider()
    assert p.stats()["retrieval_tier"] == "BOOTSTRAP"


def test_fabrica_test_y_bootstrap_entregan_inmemory():
    assert create_retrieval_provider("TEST") is not None
    assert create_retrieval_provider("BOOTSTRAP") is not None


def test_fabrica_production_falla_cerrado():
    with pytest.raises(NotImplementedError) as exc:
        create_retrieval_provider("PRODUCTION")
    assert "no está" in str(exc.value)


# ===== FASE 4: RealProviderGuard =====

class _FakeExternalOK:
    name = "fake-ok"
    is_mock = False
    is_external = True

    def health_check(self) -> dict:
        return {"provider": self.name, "available": True}


class _FakeExternalDown:
    name = "fake-down"
    is_mock = False
    is_external = True

    def health_check(self) -> dict:
        raise ConnectionError("network unreachable")


class _FakeExternalNotConfigured:
    name = "fake-scaffold"
    is_mock = False
    is_external = True

    def health_check(self) -> dict:
        raise NotImplementedError("requires API key")


class _FakeExternalUnavailable:
    name = "fake-failed"
    is_mock = False
    is_external = True

    def health_check(self) -> dict:
        return {"provider": self.name, "available": False}


class _FakeExternalNoProbe:
    name = "fake-noprobe"
    is_mock = False
    is_external = True


def test_probe_mock():
    g = RealProviderGuard(provider=MockProvider())
    assert g.probe()["state"] == "MOCK"
    assert g.is_real() is False


def test_probe_healthy():
    g = RealProviderGuard(provider=_FakeExternalOK())
    assert g.probe()["state"] == "REAL_HEALTHY"
    assert g.is_real() is True
    # cache: segunda llamada no vuelve a golpear
    assert g.probe()["state"] == "REAL_HEALTHY"


def test_probe_unavailable_red_caida():
    g = RealProviderGuard(provider=_FakeExternalDown())
    assert g.probe()["state"] == "REAL_UNAVAILABLE"
    # is_real() es de TIPO (externo construido); la salud la declara probe()
    assert g.is_real() is True
    with pytest.raises(RealProviderGuardError) as exc:
        g.require_real("prueba", probe_health=True)
    assert "REAL_UNAVAILABLE" in str(exc.value)


def test_probe_not_configured():
    g = RealProviderGuard(provider=_FakeExternalNotConfigured())
    assert g.probe()["state"] == "SCAFFOLD_NOT_CONFIGURED"
    with pytest.raises(RealProviderGuardError):
        g.require_real("prueba", probe_health=True)


def test_probe_failed():
    g = RealProviderGuard(provider=_FakeExternalUnavailable())
    assert g.probe()["state"] == "REAL_FAILED"


def test_probe_sin_health_check():
    g = RealProviderGuard(provider=_FakeExternalNoProbe())
    assert g.probe()["state"] == "SCAFFOLD_NOT_CONFIGURED"


def test_probe_cache_se_puede_frescar():
    g = RealProviderGuard(provider=_FakeExternalOK())
    first = g.probe()
    g._provider = _FakeExternalDown()
    cached = g.probe()  # usa cache
    assert cached["state"] == "REAL_HEALTHY" and cached == first
    fresh = g.probe(use_cache=False)  # sonda fresca
    assert fresh["state"] == "REAL_UNAVAILABLE"


def test_explain_state_sin_sonda_no_hace_red():
    g = RealProviderGuard(provider=_FakeExternalDown())
    state = g.explain_state()
    assert "health" not in state
    state2 = g.explain_state(probe_health=True)
    assert state2["health"]["state"] == "REAL_UNAVAILABLE"


def test_run_real_falla_cerrado_con_proveedor_caido():
    class _Boom(_FakeExternalOK):
        def chat(self, *a, **k):
            raise ConnectionError("down")

    g = RealProviderGuard(provider=_Boom())
    resp = g.run_real(prompt="test")
    assert resp.text == ""
    assert RealProviderGuard.is_response_failed(resp) is True


def test_router_incluye_proveedor_real():
    from albra.llm.router import _PROVIDER_CLASSES

    assert "nvidia" in _PROVIDER_CLASSES
