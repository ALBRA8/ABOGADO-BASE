"""BATERÍA DE CASOS JURÍDICOS REALES — 8 dominios (Fase Producción Real).

Cada caso: consulta jurídica REAL sobre el corpus canónico (21 docs,
8114 arts, 10 sentencias) → el agente debe responder CON evidencia
verificada (literal_retraced), análisis jurídico estructurado y auditoría
de citas en verde. La abstención en un dominio cubierto es un FALLO de
cobertura/retrieval, no una virtud aquí.
"""
from __future__ import annotations

import pytest

from albra.eval.legal_rubric import evaluate_legal_response
from albra.knowledge.corpus_seed import build_seeded_retriever
from albra.knowledge.legal_engine import LegalKnowledgeEngine
from albra.knowledge.response_policy import decide_response_policy

# (dominio, consulta, fragmento esperado en la cita/evidencia)
BATTERY = [
    ("CIVIL", "¿Qué establece el artículo 1602 del Código Civil sobre los contratos?", "1602"),
    ("LABORAL", "¿Qué establece el artículo 23 del Código Sustantivo del Trabajo sobre los elementos esenciales del contrato de trabajo?", "23"),
    ("PENAL", "¿Qué establece el artículo 32 de la Ley 599 de 2000 sobre la favorabilidad?", "32"),
    ("PROCESAL", "¿Qué establece el artículo 2 de la Ley 1437 de 2011 sobre el procedimiento administrativo?", "2"),
    ("ADMINISTRATIVO", "¿Qué establece el artículo 1 de la Ley 1437 de 2011?", "1"),
    ("CONSTITUCIONAL", "¿Qué establece el artículo 25 de la Constitución Política sobre el derecho al trabajo?", "25"),
    ("COMERCIAL", "¿Qué establece el artículo 1 del Decreto 410 de 1971 sobre los comerciantes?", "1"),
    ("SEGURIDAD_SOCIAL", "¿Qué establece el artículo 1 de la Ley 100 de 1993 sobre la seguridad social?", "1"),
]


@pytest.fixture(scope="module")
def _engine():
    async def _build():
        retriever, report = await build_seeded_retriever()
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        return retriever, engine

    import asyncio

    retriever, engine = asyncio.run(_build())
    yield engine
    asyncio.run(engine.shutdown())
    asyncio.run(retriever.provider.shutdown())


@pytest.mark.parametrize(("dominio", "query", "art"), BATTERY)
def test_caso_por_dominio(_engine, dominio, query, art):
    """Cada dominio cubierto se responde con evidencia verificada."""
    import asyncio

    r = asyncio.run(_engine.query(query))
    assert r.abstention is False, (
        f"{dominio}: dominio CUBIERTO por el corpus no puede abstenerse: "
        f"{r.abstention_reason}"
    )
    audit = r.citation_audit or {}
    assert audit.get("all_verified") is True, (dominio, audit.get("reason"))
    assert audit.get("fidelity", {}).get("literal_retraced", 0) >= 1
    analysis = r.legal_analysis or {}
    assert analysis.get("normas_aplicables"), dominio
    assert any(art in n["citation"] for n in analysis["normas_aplicables"]), (
        f"{dominio}: el art. {art} debe aparecer en las normas aplicables"
    )


def test_bateria_responde_los_8_dominios(_engine):
    """La batería COMPLETA responde 8/8 dominios con evidencia."""
    import asyncio

    results = {}
    for dominio, query, _art in BATTERY:
        r = asyncio.run(_engine.query(query))
        results[dominio] = not r.abstention
    assert all(results.values()), results


def test_rubrica_sobre_respuesta_buena(_engine):
    """FASE 9: la rúbrica sobre una respuesta de la batería NO es FAIL."""
    import asyncio

    r = asyncio.run(_engine.query(BATTERY[0][1]))
    result = evaluate_legal_response(r.as_dict() if hasattr(r, "as_dict") else vars(r))
    assert result.hallucinated_authority is False
    assert result.verdict in ("READY", "CONDITIONAL")
    assert set(result.scores.keys()) >= {
        "issue_identification", "applicable_law", "citation_accuracy",
        "abstention", "human_escalation",
    }


def test_politica_respuesta_answer_limpio():
    """FASE 10: evidencia limpia → ANSWER sin advertencias."""
    pol = decide_response_policy(
        abstention=False,
        citation_audit={"executed": True, "all_verified": True},
        verification_confidence=0.9,
        query_text="¿Qué dice el artículo 25 de la Constitución?",
    )
    assert pol["decision"] == "ANSWER"
    assert pol["warnings"] == []


def test_politica_respuesta_warning_fecha_aproximada():
    pol = decide_response_policy(
        abstention=False,
        citation_audit={"executed": True, "all_verified": True},
        verification_confidence=0.9,
        temporal_approx=True,
    )
    assert pol["decision"] == "ANSWER_WITH_WARNING"
    assert any("aproximada" in w for w in pol["warnings"])


def test_politica_respuesta_abstain_sin_evidencia():
    pol = decide_response_policy(abstention=True)
    assert pol["decision"] == "ABSTAIN"


def test_politica_respuesta_abstain_cita_no_verificada():
    pol = decide_response_policy(
        abstention=False,
        citation_audit={"executed": True, "all_verified": False, "unverified": 1},
    )
    assert pol["decision"] == "ABSTAIN"


def test_politica_respuesta_human_review_conflictos():
    pol = decide_response_policy(
        abstention=False,
        citation_audit={"executed": True, "all_verified": True},
        has_conflicts=True,
    )
    assert pol["decision"] == "HUMAN_REVIEW_REQUIRED"


def test_politica_respuesta_human_review_materia_riesgo():
    pol = decide_response_policy(
        abstention=False,
        citation_audit={"executed": True, "all_verified": True},
        query_text="¿Qué pena recibo por hurto calificado agravado?",
    )
    assert pol["decision"] == "HUMAN_REVIEW_REQUIRED"


def test_politica_precedencia_protectora():
    """ABSTAIN nunca se degrada aunque haya warnings disponibles."""
    pol = decide_response_policy(
        abstention=True, temporal_approx=True, has_conflicts=True
    )
    assert pol["decision"] == "ABSTAIN"
