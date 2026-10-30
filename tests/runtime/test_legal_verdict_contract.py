"""Tests del contrato de respuesta jurídica — hallazgo 6 (P1) del cierre.

Separación de semánticas en la respuesta de una consulta jurídica a
través de ``Agent.process()`` (ruta real, NO engine directo):

- ``legal_gate``: AUTORIZACIÓN para invocar el motor (LegalGate).
- ``legal_verdict``: RESULTADO de la investigación jurídica:
  ANSWERED_WITH_EVIDENCE | ABSTAINED | NEEDS_HUMAN_REVIEW | GATE_BLOCKED.

La autorización de ejecución NUNCA se presenta como aprobación
jurídica: abstention=True ⇒ legal_verdict == ABSTAINED (antes la ruta
devolvía ``legal_verdict="APPROVED"`` fijo incluso con abstención).
"""
from __future__ import annotations

import asyncio

import pytest

from albra.identity.agent import Agent


@pytest.fixture
def strong_secrets(monkeypatch):
    monkeypatch.setenv("ALBRA_JWT_SECRET", "test-ephemeral-jwt-secret-32-chars")
    monkeypatch.setenv("ALBRA_ADMIN_PASSWORD", "test-ephemeral-pass-1234")


@pytest.fixture
def in_memory_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("ALBRA_MEMORY_PATH", str(tmp_path / "memory.db"))
    monkeypatch.setenv("ALBRA_AUDIT_PATH", str(tmp_path / "audit.jsonl"))


def _agent(strong_secrets, in_memory_storage):
    agent = Agent()
    asyncio.run(agent.boot())
    return agent


def test_answered_with_evidence_verdict(strong_secrets, in_memory_storage):
    agent = _agent(strong_secrets, in_memory_storage)
    result = asyncio.run(agent.process(
        "¿Qué dice el artículo 25 de la Constitución Política?",
        user_role="admin",
    ))
    assert result["routed_to"] == "legal_engine"
    assert result["abstention"] is False
    assert result["legal_verdict"] == "ANSWERED_WITH_EVIDENCE"
    assert result["legal_gate"] in ("APPROVED", "APPROVED_WITH_LIMITS", "REVIEW_REQUIRED")
    asyncio.run(agent.shutdown())


def test_abstention_verdict_is_not_approved(strong_secrets, in_memory_storage):
    """REGRESIÓN P1-6: con abstención, legal_verdict NO puede ser APPROVED."""
    # Ley 1952 de 2019 (Código General Disciplinario): norma REAL de CO
    # que NO está en el corpus canónico → abstención obligatoria.
    agent = _agent(strong_secrets, in_memory_storage)
    result = asyncio.run(agent.process(
        "¿Qué establece el artículo 66 de la Ley 1952 de 2019 sobre el régimen disciplinario?",
        user_role="admin",
    ))
    assert result["routed_to"] == "legal_engine"
    assert result["abstention"] is True
    assert result["legal_verdict"] == "ABSTAINED"
    assert result["legal_verdict"] != "APPROVED"
    asyncio.run(agent.shutdown())


def test_verdict_values_are_from_documented_set(strong_secrets, in_memory_storage):
    agent = _agent(strong_secrets, in_memory_storage)
    valid = {"ANSWERED_WITH_EVIDENCE", "ABSTAINED", "NEEDS_HUMAN_REVIEW", "GATE_BLOCKED"}
    for query in (
        "¿Qué dice el artículo 25 de la Constitución Política?",
        "¿Qué establece el artículo 66 de la Ley 1952 de 2019 sobre el régimen disciplinario?",
    ):
        result = asyncio.run(agent.process(query, user_role="admin"))
        if result.get("routed_to") == "legal_engine":
            assert result["legal_verdict"] in valid, (
                f"legal_verdict fuera del contrato: {result['legal_verdict']}"
            )
    asyncio.run(agent.shutdown())


def test_consistency_between_abstention_and_verdict(strong_secrets, in_memory_storage):
    """Invariante del contrato: abstention ⟹ legal_verdict == ABSTAINED."""
    agent = _agent(strong_secrets, in_memory_storage)
    for query in (
        "¿Qué dice el artículo 25 de la Constitución Política?",
        "¿Qué establece el artículo 66 de la Ley 1952 de 2019 sobre el régimen disciplinario?",
        "¿Qué establece el artículo 23 del Código Sustantivo del Trabajo?",
    ):
        result = asyncio.run(agent.process(query, user_role="admin"))
        if result.get("routed_to") == "legal_engine":
            if result["abstention"]:
                assert result["legal_verdict"] == "ABSTAINED"
            else:
                assert result["legal_verdict"] in (
                    "ANSWERED_WITH_EVIDENCE", "NEEDS_HUMAN_REVIEW",
                )
    asyncio.run(agent.shutdown())
