"""PRUEBA INTEGRAL DEL AGENTE — cierre de extracción ABOGADO-BASE (P0).

Equivalente funcional de ``DESPACHO-JURIDICO/tests/test_agent_integration.py``
(adaptado al abogado independiente), verificando el RECORRIDO REAL:

    Agent.boot() → corpus_seed → LegalKnowledgeEngine → Runtime →
    Agent.process()

Qué verifica (hallazgo 3 del PROMPT MAESTRO):

- Arranque real del agente (todos los órganos).
- ``legal_corpus_report`` disponible con ``seed_failed == False``.
- 12 documentos sembrados (V1.4 + leyes V1.3 vivas).
- 2.200 artículos indexados.
- Consulta jurídica reconocida y enrutada a ``legal_engine``.
- Recuperación de evidencia REAL del corpus (no abstención espuria).
- Cita formal + provenance (hash, source_url, tier, vigencia).
- Estado de abstención correcto cuando la fuente NO está en el corpus.
- Contrato de respuesta jurídica (legal_gate ≠ legal_verdict).
- Apagado limpio del agente.

NO sustituye esta prueba una prueba que construya directamente el
``LegalKnowledgeEngine``: el recorrido pasa por ``Agent.process()``.
"""
from __future__ import annotations

import asyncio

import pytest

from albra.identity.agent import Agent
from albra.identity.manifest import AGENT_MANIFEST

CANONICAL_DOCS = 21
CANONICAL_ARTICLES = 8114


@pytest.fixture
def strong_secrets(monkeypatch):
    monkeypatch.setenv("ALBRA_JWT_SECRET", "test-ephemeral-jwt-secret-32-chars")
    monkeypatch.setenv("ALBRA_ADMIN_PASSWORD", "test-ephemeral-pass-1234")


@pytest.fixture
def in_memory_storage(monkeypatch, tmp_path):
    """Memoria/audit efímeros para no tocar data/ real."""
    monkeypatch.setenv("ALBRA_MEMORY_BACKEND", "sqlite")
    monkeypatch.setenv("ALBRA_MEMORY_PATH", str(tmp_path / "memory.db"))
    monkeypatch.setenv("ALBRA_AUDIT_PATH", str(tmp_path / "audit.jsonl"))


def _run(coro):
    return asyncio.run(coro)


def test_agent_boots_all_organs(strong_secrets, in_memory_storage):
    """Criterio: el agente nace con todos los órganos (ADN universal)."""
    agent = Agent()
    _run(agent.boot())
    expected = (
        "runtime", "reasoning", "tools", "capabilities",
        "mcp_server", "memory", "doctor", "events", "workflows",
        "providers", "security", "audit", "research", "evidence",
        "files", "comms", "resilience",
        # Órganos jurídicos del cierre de extracción:
        "legal_engine", "legal_retriever", "legal_corpus_report",
    )
    for organ in expected:
        assert organ in agent.organs, f"Falta órgano: {organ}"
    _run(agent.shutdown())


def test_agent_boot_seeds_canonical_corpus(strong_secrets, in_memory_storage):
    """P0: boot REAL siembra el corpus canónico — reporte verificable."""
    agent = Agent()
    _run(agent.boot())
    report = agent.organs.get("legal_corpus_report")
    assert report is not None, "legal_corpus_report no disponible tras boot"
    # seed_failed EXPLÍCITO y False en la ruta exitosa.
    assert report.get("seed_failed") is False, (
        f"seed_failed debe ser False en ruta exitosa: {report}"
    )
    assert report.get("ingested") == CANONICAL_DOCS, (
        f"12 documentos sembrados esperados, got {report.get('ingested')}"
    )
    stats = report.get("stats", {})
    assert stats.get("articles") == CANONICAL_ARTICLES, (
        f"8.114 artículos indexados esperados, got {stats.get('articles')}"
    )
    assert report.get("corpus_version") == "V1.5+V1.4"
    # Sin documentos con hash inválido ni rechazados (integridad).
    assert report.get("skipped_hash_mismatch") == []
    assert report.get("rejected") == []
    # Integridad de hashes verificable de forma independiente.
    from albra.knowledge.corpus_seed import verify_corpus_hashes
    assert verify_corpus_hashes() == []
    _run(agent.shutdown())


def test_agent_legal_query_full_route(strong_secrets, in_memory_storage):
    """P0: consulta jurídica REAL — boot → seed → engine → runtime → respuesta.

    Verifica: reconocimiento, enrutamiento a legal_engine, recuperación
    de evidencia real, cita + provenance, auditoría de citas y
    veredicto del contrato.
    """
    agent = Agent()
    _run(agent.boot())
    result = _run(agent.process(
        "¿Qué dice el artículo 25 de la Constitución Política sobre el trabajo?",
        user="test", user_role="admin",
    ))
    # Enrutamiento a legal_engine (NO a reasoning fallback).
    assert result.get("routed_to") == "legal_engine", (
        f"Debe rutear a legal_engine, got routed_to={result.get('routed_to')}"
    )
    assert result.get("abstention") is False
    # Contrato de respuesta jurídica (hallazgo 6): autorización ≠ resultado.
    assert result.get("legal_verdict") == "ANSWERED_WITH_EVIDENCE", (
        f"legal_verdict={result.get('legal_verdict')}"
    )
    assert result.get("legal_gate") in (
        "APPROVED", "APPROVED_WITH_LIMITS", "REVIEW_REQUIRED",
    ), f"legal_gate={result.get('legal_gate')}"
    # La respuesta contiene el texto normativo REAL del corpus.
    reply = result["reply"]
    assert "trabajo" in reply.lower(), f"Sin texto normativo real: {reply[:200]}"

    # La comprobación dura de provenance se hace sobre el organ
    # legal_engine (fuente única del recorrido real).
    engine = agent.organs["legal_engine"]
    response = _run(engine.query(
        "¿Qué dice el artículo 25 de la Constitución Política sobre el trabajo?",
    ))
    assert response.abstention is False
    assert response.blocks, "Sin bloques de respuesta"
    norm_block = next(
        (b for b in response.blocks if b.content_type == "texto_normativo"), None,
    )
    assert norm_block is not None, "Sin bloque de texto normativo"
    assert norm_block.citations, "Sin cita formal en el bloque normativo"
    citation = norm_block.citations[0]
    # Provenance completa: documento, tier, hash, vigencia, URL.
    assert citation.document_id, "citation sin document_id"
    assert citation.source_tier == "S0_PRIMARY_SUPERIOR"
    assert citation.content_hash, "citation sin content_hash (provenance)"
    assert citation.source_url, "citation sin source_url (provenance)"
    assert citation.status == "vigente"
    assert citation.is_current is True
    # Auditoría de citas pre-reveal ejecutada (hallazgo 7).
    audit = response.citation_audit
    assert audit.get("executed") is True
    assert audit.get("all_verified") is True
    assert audit.get("fidelity", {}).get("literal_retraced", 0) >= 1
    # Análisis jurídico estructurado presente (hallazgo 4).
    analysis = response.legal_analysis
    assert analysis, "legal_analysis vacío"
    assert analysis.get("problemas_juridicos")
    assert analysis.get("normas_aplicables")
    assert analysis.get("argumentos")
    assert analysis.get("conclusion")
    assert analysis.get("conclusion_con_soporte") is True
    assert analysis.get("llm_usado") is False
    _run(agent.shutdown())


def test_agent_legal_query_abstains_without_evidence(strong_secrets, in_memory_storage):
    """P0: consulta jurídica sin corpus aplicable → abstención correcta.

    La Ley 1952 de 2019 (Código General Disciplinario) es una norma REAL
    de CO que NO está en el corpus canónico; el agente NO inventa.
    """
    agent = Agent()
    _run(agent.boot())
    result = _run(agent.process(
        "¿Qué establece el artículo 66 de la Ley 1952 de 2019 sobre el régimen disciplinario?",
        user="test", user_role="admin",
    ))
    assert result.get("routed_to") == "legal_engine"
    assert result.get("abstention") is True
    assert result.get("legal_verdict") == "ABSTAINED", (
        f"abstention=True debe producir legal_verdict=ABSTAINED, "
        f"got {result.get('legal_verdict')}"
    )
    reply_lower = result["reply"].lower()
    assert "abstención" in reply_lower or "no se encontró" in reply_lower or "evidencia" in reply_lower
    _run(agent.shutdown())


def test_agent_degraded_seed_is_explicit(strong_secrets, in_memory_storage, monkeypatch):
    """P0: fallo de siembra → arranque degradado EXPLÍCITO (nivel 2).

    seed_failed=True + provider vacío + corpus_version='unseeded'.
    La consulta jurídica subsiguiente abstuvo (fail-closed de nivel
    respuesta) y el estado del servicio NO se anuncia disponible.
    """
    async def _boom():
        raise RuntimeError("simulated seed failure (test)")

    from albra.knowledge import corpus_seed
    monkeypatch.setattr(corpus_seed, "build_seeded_retriever", _boom)
    agent = Agent()
    _run(agent.boot())
    report = agent.organs.get("legal_corpus_report", {})
    assert report.get("seed_failed") is True
    assert report.get("corpus_version") == "unseeded"
    assert report.get("ingested") == 0
    assert "simulated seed failure" in report.get("error", "")
    # Readiness del servicio jurídico: NO se anuncia disponible.
    engine = agent.organs["legal_engine"]
    stats = engine.stats()
    assert stats.get("corpus_available") is False
    assert stats.get("legal_service") == "DEGRADED_NO_CORPUS"
    # Fail-closed de nivel respuesta: sin corpus → abstención.
    result = _run(agent.process(
        "¿Qué dice el artículo 25 de la Constitución Política?",
        user="test", user_role="admin",
    ))
    assert result.get("routed_to") == "legal_engine"
    assert result.get("abstention") is True
    assert result.get("legal_verdict") == "ABSTAINED"
    _run(agent.shutdown())


def test_agent_cst_article_recovered_after_connection_fix(strong_secrets, in_memory_storage):
    """Regresión del fix de conexión: consulta por TÍTULO de norma.

    Antes: el clasificador emitía 'Código Sustantivo del Trabajo' y la
    búsqueda exacta solo comparaba contra norm.number ('Decreto 2663 de
    1950') → 0 hits → abstención espuria. Ahora recupera evidencia real.
    """
    agent = Agent()
    _run(agent.boot())
    result = _run(agent.process(
        "¿Qué establece el artículo 23 del Código Sustantivo del Trabajo?",
        user="test", user_role="admin",
    ))
    assert result.get("routed_to") == "legal_engine"
    assert result.get("abstention") is False, (
        f"CST art. 23 ESTÁ en el corpus; no debe abstenerse: {result['reply'][:150]}"
    )
    assert result.get("legal_verdict") == "ANSWERED_WITH_EVIDENCE"
    _run(agent.shutdown())


def test_agent_processes_greeting(strong_secrets, in_memory_storage):
    agent = Agent()
    _run(agent.boot())
    result = _run(agent.process("hola, qué más"))
    assert result["authorized"] is True
    assert "ALBRA" in result["reply"]
    _run(agent.shutdown())


def test_agent_writes_memory_and_audit(strong_secrets, in_memory_storage):
    agent = Agent()
    _run(agent.boot())
    _run(agent.process("hola"))
    stats = agent.organs["memory"].stats()
    assert stats.get("total", 0) >= 1
    items = agent.organs["audit"].read(limit=10)
    assert len(items) >= 1
    _run(agent.shutdown())


def test_agent_shutdown_clean(strong_secrets, in_memory_storage):
    """P0: apagado limpio — todos los órganos con shutdown se apagan."""
    agent = Agent()
    _run(agent.boot())
    _run(agent.process("hola"))
    _run(agent.shutdown())
    assert agent._booted is False


def test_agent_identity_not_constructor():
    """Criterio 35: NO modifica la fuente de verdad fuera del Constructor."""
    assert AGENT_MANIFEST.is_constructor is False
    assert AGENT_MANIFEST.can_modify_code is False
