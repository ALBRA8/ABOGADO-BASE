"""Tests FASE 5 (issue discovery) y FASE 6 (jurisprudencia real).

FASE 5: la autonomía del LawyerExam distingue ISSUE_DETECTED /
ISSUE_PROPOSED / ISSUE_VERIFIED — una hipótesis del agente nunca se
presenta como hecho jurídico confirmado.

FASE 6: los metadatos de las 10 sentencias reales del corpus
(expediente, ponentes, sala, fecha) se extraen del texto de la fuente
— nada inventado; lo ausente queda None — y el retrieval enriquecido
expone ponente/fecha reales.
"""
from __future__ import annotations

import pytest

from albra.knowledge.jurisprudence_metadata import (
    classify_precedent,
    corpus_jurisprudence_metadata,
    extract_sentencia_metadata,
)

# ===== FASE 5: estados de issue discovery =====

def _exam_issue_states():
    """Lee los marcadores reales del issue_discovery (sin hardcodear)."""
    import inspect

    from albra.lawyer import issue_discovery as mod

    src = inspect.getsource(mod)
    return src


def test_issue_discovery_declara_los_tres_estados():
    src = _exam_issue_states()
    assert "proposed_by_agent" in src, "las propuestas del agente deben marcarse"
    assert "verified" in src, "la verificación contra corpus debe existir"


def test_issue_descubrimiento_marca_propuestas_como_no_verificadas():
    """Toda propuesta del agente nace proposed_by_agent=True/verified=False."""
    from albra.lawyer.issue_discovery import (
        discover_legal_issues,
        propose_required_sources,
    )

    case = {
        "facts": [
            "Trabajador despedido sin causa justa el 10 de enero de 2024 "
            "tras cinco años de servicio. No le pagaron las prestaciones.",
        ],
        "documents": [],
        "uncertainties": [],
    }
    issues = discover_legal_issues(case)
    assert issues, "el descubrimiento debe proponer al menos un problema"
    for it in issues:
        assert it.get("proposed_by_agent") is True
        # el issue propuesto NO nace verificado (la verificación ocurre
        # en el paso 5 del examen contra el corpus)
        assert "verified" not in it or it.get("verified") is False
    sources = propose_required_sources(case, issues)
    for s in sources:
        assert s.get("proposed_by_agent") is True
        assert s.get("verified") is False


# ===== FASE 6: metadatos reales de sentencias =====

def test_diez_sentencias_con_provenance_oficial():
    metas = corpus_jurisprudence_metadata()
    assert len(metas) == 10
    for m in metas:
        assert m["verification"] == "VERIFIED"
        assert (
            "corteconstitucional.gov.co" in m["source_url"]
        ), m["sentencia_id"]
        assert len(m["content_hash"]) == 64


def test_fecha_extraida_del_texto_real():
    """Las fechas provienen del texto ('Bogotá, DC, treinta y uno (31) de
    julio de dos mil ocho (2008)' → 2008-07-31) — nunca se rellenan."""
    by_id = {m["sentencia_id"]: m for m in corpus_jurisprudence_metadata()}
    assert by_id["T-760-2008"]["fecha_resolucion"] == "2008-07-31"
    assert by_id["C-355-2006"]["fecha_resolucion"] == "2006-05-10"
    assert by_id["T-001-2020"]["fecha_resolucion"] == "2020-01-14"
    # lo que la fuente no declara queda None (SU-360/99, formato distinto)
    assert by_id["SU-360-1999"]["fecha_resolucion"] is None


def test_ponentes_reales():
    by_id = {m["sentencia_id"]: m for m in corpus_jurisprudence_metadata()}
    pon = by_id["T-760-2008"]["ponentes"]
    assert pon and "CEPEDA" in pon[0].upper()
    pon355 = by_id["C-355-2006"]["ponentes"]
    assert pon355 and len(pon355) == 2  # ponentes dobles (C-355)


def test_expediente_real_distinto_del_id_citacion():
    by_id = {m["sentencia_id"]: m for m in corpus_jurisprudence_metadata()}
    # T-760/08: radicado interno real T-1315769 (≠ id de citación)
    assert by_id["T-760-2008"]["expediente"] == "T-1315769"
    assert by_id["T-001-2020"]["expediente"] == "T-7.514.242"


def test_extract_metadata_sin_texto_devuelve_nones():
    meta = extract_sentencia_metadata("")
    assert meta["expediente"] is None
    assert meta["ponentes"] is None
    assert meta["fecha_resolucion"] is None


# ===== clasificación de precedente =====

def test_classify_precedent_matriz():
    assert classify_precedent(verified=False, force=None) == "NO_VERIFICADA"
    assert (
        classify_precedent(verified=True, force="erga_omnes+vinculante")
        == "VINCULANTE"
    )
    assert classify_precedent(verified=True, force="persuasivo") == "PERSUASIVA"
    assert (
        classify_precedent(
            verified=True, force="erga_omnes+vinculante", in_conflict=True
        )
        == "CONTRADICTORIA"
    )


def test_corpus_sentencias_son_vinculantes_o_persuasivas():
    for m in corpus_jurisprudence_metadata():
        v = classify_precedent(verified=True, force=m["force"])
        assert v in ("VINCULANTE", "PERSUASIVA"), (m["sentencia_id"], v)


# ===== enriquecimiento del retrieval =====

@pytest.mark.asyncio
async def test_seed_enriquece_ponente_y_fecha_reales():
    from albra.knowledge.corpus_seed import build_seeded_retriever

    retriever, report = await build_seeded_retriever()
    try:
        assert report.ingested == 21
        enriched = {
            j.file_number: j
            for j in retriever.provider.jurisprudence_items()
        }
        t760 = enriched.get("T-760-2008")
        assert t760 is not None
        assert t760.ponente and "CEPEDA" in t760.ponente.upper()
        assert str(t760.decision_date) == "2008-07-31"
    finally:
        await retriever.provider.shutdown()
