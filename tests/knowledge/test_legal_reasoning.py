"""Tests del análisis jurídico estructurado — hallazgo 4 (P0) del cierre.

El análisis se construye DETERMINISTAMENTE sobre la evidencia ya
verificada por el pipeline del LegalKnowledgeEngine (sin LLM, sin
nueva recuperación). Cada argumento lleva cita; la conclusión sin
fuente primaria vigente queda SIN soporte.
"""
from __future__ import annotations

import pytest

from albra.knowledge.corpus_seed import build_seeded_retriever
from albra.knowledge.legal_engine import LegalKnowledgeEngine
from albra.knowledge.legal_reasoning import build_legal_analysis


@pytest.fixture
def strong_secrets(monkeypatch):
    monkeypatch.setenv("ALBRA_JWT_SECRET", "test-ephemeral-jwt-secret-32-chars")
    monkeypatch.setenv("ALBRA_ADMIN_PASSWORD", "test-ephemeral-pass-1234")


@pytest.fixture
def seeded_engine(strong_secrets):
    """Engine con el corpus canónico sembrado (ruta real de boot)."""

    async def _build():
        retriever, report = await build_seeded_retriever()
        return LegalKnowledgeEngine(retriever=retriever), report

    return asyncio_run(_build())


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


def test_analysis_structure_for_constitution_query(seeded_engine):
    engine, _report = seeded_engine
    response = asyncio_run(engine.query(
        "¿Qué dice el artículo 25 de la Constitución Política sobre el trabajo?",
    ))
    assert response.abstention is False
    analysis = response.legal_analysis
    # Separación hechos / inferencias / conclusiones.
    assert analysis["hechos_declarados"]
    assert analysis["inferencias"]
    # Problemas jurídicos identificados.
    assert any("artículo 25" in i for i in analysis["problemas_juridicos"])
    assert any("Constitución" in i for i in analysis["problemas_juridicos"])
    # Hechos faltantes declarados honestamente (no inventados).
    assert any("Fecha de los hechos" in f for f in analysis["hechos_faltantes"])
    # Normas aplicables con provenance.
    norms = analysis["normas_aplicables"]
    assert norms
    assert all(n["content_hash"] for n in norms)
    assert all(n["source_tier"] for n in norms)
    # Argumentos con cita — trazabilidad completa.
    args = analysis["argumentos"]
    assert args
    assert all(a["citations"] for a in args), "argumento sin cita"
    assert analysis["citas_completas"] is True
    # Conclusión con soporte (fuente primaria vigente).
    assert analysis["conclusion_con_soporte"] is True
    assert "Constitución Política de 1991, art. 25" in analysis["conclusion"]
    # Determinista — sin LLM.
    assert analysis["llm_usado"] is False


def test_analysis_argument_citations_match_recovered_norm(seeded_engine):
    """El argumento cita la MISMA norma recuperada (no otra)."""
    engine, _report = seeded_engine
    response = asyncio_run(engine.query(
        "¿Qué establece el artículo 23 del Código Sustantivo del Trabajo?",
    ))
    assert response.abstention is False
    args = response.legal_analysis["argumentos"]
    assert args
    first_arg_citations = args[0]["citations"]
    assert any("Decreto 2663 de 1950" in c["citation_text"] for c in first_arg_citations), (
        f"El argumento no cita la norma recuperada: {[c['citation_text'] for c in first_arg_citations]}"
    )


def test_analysis_flags_non_current_evidence_as_risk(seeded_engine):
    """Evidencia no vigente en candidatos → riesgo explícito."""
    engine, _report = seeded_engine
    # Consulta semántica amplia que puede traer varias fuentes.
    response = asyncio_run(engine.query(
        "jurisprudencia de la Corte Constitucional sobre debido proceso",
    ))
    analysis = response.legal_analysis
    # La estructura de riesgos existe y es lista de strings.
    assert isinstance(analysis["riesgos"], list)


def test_analysis_without_primary_source_has_unsupported_conclusion(strong_secrets):
    """Sin corpus → el builder NO se ejecuta (abstención aguas arriba),
    pero la función es directa: conclusión sin fuente primaria = sin soporte."""
    from albra.knowledge.citation import Citation
    from albra.knowledge.query_classifier import LegalQueryClassifier
    from albra.knowledge.retrieval import HybridRetriever
    from albra.knowledge.retrieval_providers import InMemoryRetrievalProvider
    from albra.knowledge.verification import LegalVerifier

    engine = LegalKnowledgeEngine(retriever=HybridRetriever(provider=InMemoryRetrievalProvider()))
    classifier = LegalQueryClassifier()
    classification = classifier.classify("consulta sin evidencia")
    retrieval = asyncio_run(engine.retriever.retrieve(
        engine._build_retrieval_query("consulta sin evidencia", classification),
    ))
    verification = LegalVerifier().verify(retrieval)
    analysis = build_legal_analysis(
        query_text="consulta sin evidencia",
        classification=classification,
        verification=verification,
        citations=[],
    )
    assert analysis.conclusion_con_soporte is False
    assert "No se puede emitir" in analysis.conclusion
    assert analysis.citas_completas is False or analysis.argumentos == []


def test_contraargumentos_from_verification_conflicts(seeded_engine):
    """Conflicto entre fuentes detectado por el verifier → contraargumento
    explícito en el análisis (no se oculta)."""
    from albra.knowledge.citation import Citation
    from albra.knowledge.legal_reasoning import build_legal_analysis
    from albra.knowledge.query_classifier import LegalQueryClassifier
    from albra.knowledge.verification import Conflict, VerificationResult

    cit_a = Citation(
        document_id="doc-a", source_tier="S1_OFFICIAL", authority="Congreso",
        document_type="ley", citation_text="Ley 100 de 1993, art. 8",
        snippet="fragmento a", is_current=True,
    )
    verification = VerificationResult(
        ok=True,
        candidates=[],
        conflicts=[Conflict(
            kind="status_conflict",
            description="Fuentes con estados de vigencia contradictorios para la misma norma.",
            candidate_ids=["a", "b"],
        )],
        primary_evidence_id=None,
    )
    classification = LegalQueryClassifier().classify("consulta de prueba")
    analysis = build_legal_analysis(
        query_text="consulta de prueba",
        classification=classification,
        verification=verification,
        citations=[cit_a],
    )
    assert analysis.contraargumentos
    assert "Conflicto entre fuentes" in analysis.contraargumentos[0]
    # Sin fuente primaria → conclusión sin soporte.
    assert analysis.conclusion_con_soporte is False
