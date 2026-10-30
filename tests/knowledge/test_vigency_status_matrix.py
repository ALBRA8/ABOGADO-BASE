"""Tests de vigencia y fuentes oficiales — hallazgo 8 del cierre.

Distingue explícitamente (sin inventar integraciones):
- Estado de vigencia ALMACENADO (VALIDITY_STATUS completo).
- Vigencia histórica vs vigente vs as_of.
- Fecha de entrada en vigor, derogación, modificación, suspensión,
  inexequibilidad, información pendiente.
- Catálogo de fuentes: DECLARATIVO (URLs vacías, sin conectividad
  simulada) vs fetcher real de ingestion_colombia (infraestructura
  existente, sin claims de tiempo real).
"""
from __future__ import annotations

from datetime import date

import pytest

from albra.knowledge.schemas import VALIDITY_STATUS
from albra.knowledge.temporal import (
    TemporalQuery,
    TemporalState,
    is_currently_vigente,
    is_historical,
    is_vigente,
    normalize_status,
)
from albra.knowledge.vigency import VigencyChecker

# ===== VALIDITY_STATUS — los 10 estados existen =====

def test_validity_status_covers_all_required_distinctions():
    required = {
        "vigente", "derogada", "modificada", "sustituida", "suspendida",
        "inexequible", "nula", "perdida_vigencia", "historica", "pendiente",
    }
    assert required.issubset(set(VALIDITY_STATUS))


def test_normalize_status_distinguishes_all_states():
    pairs = {
        "derogado": "derogada",
        "modificado": "modificada",
        "sustituido": "sustituida",
        "suspendido": "suspendida",
        "inexequible": "inexequible",
        "nula": "nula",
        "historica": "historica",
        "pendiente": "pendiente",
        "vigente": "vigente",
    }
    for raw, expected in pairs.items():
        assert normalize_status(raw) == expected


# ===== Vigencia temporal =====

def test_vigente_status_effective_from():
    """Fecha de entrada en vigor: antes NO vigente; después vigente."""
    eff = date(2012, 7, 23)
    assert is_vigente(status="vigente", effective_from=eff, effective_until=None,
                      when=date(2012, 1, 1)) is False
    assert is_vigente(status="vigente", effective_from=eff, effective_until=None,
                      when=date(2013, 1, 1)) is True


def test_derogada_not_current():
    assert is_currently_vigente(
        status="derogada", effective_from=date(1990, 1, 1),
        effective_until=date(2000, 1, 1),
    ) is False


def test_suspendida_not_current():
    assert is_currently_vigente(
        status="suspendida", effective_from=None, effective_until=None,
    ) is False


def test_inexequible_not_current():
    assert is_currently_vigente(
        status="inexequible", effective_from=None, effective_until=None,
    ) is False


def test_historical_query_never_returns_current():
    state = TemporalState(
        status="vigente",
        effective_from=date(1991, 7, 5),
        effective_until=None,
    )
    q_hist = TemporalQuery(query_type="historical")
    # Norma vigente no satisface una consulta histórica.
    assert q_hist.matches(state) is False
    q_current = TemporalQuery(query_type="current")
    assert q_current.matches(state) is True


def test_as_of_query_uses_historical_validity():
    """Consulta as_of: la norma estaba vigente en la fecha dada."""
    state = TemporalState(
        status="derogada",
        effective_from=date(1936, 1, 1),
        effective_until=date(2000, 6, 30),
    )
    q = TemporalQuery(query_type="as_of", as_of=date(1995, 1, 1))
    assert q.matches(state) is True  # estaba vigente en 1995
    q2 = TemporalQuery(query_type="as_of", as_of=date(2010, 1, 1))
    assert q2.matches(state) is False  # ya derogada


def test_is_historical_marks_expired():
    assert is_historical(status="vigente", effective_until=date(2005, 1, 1)) is True
    assert is_historical(status="historica", effective_until=None) is True
    assert is_historical(status="vigente", effective_until=None) is False


# ===== VigencyChecker (marcadores en texto del artículo) =====

def _doc(status="vigente", effective_until=None):
    return {"status": status, "effective_until": effective_until}


def test_checker_document_level_vigent():
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article=None)
    assert result.status == "vigent"
    assert result.evidence_source == "document_metadata"


def test_checker_effective_until_is_superseded():
    checker = VigencyChecker()
    result = checker.check(document=_doc(effective_until="2001-12-31"), article=None)
    assert result.status == "superseded"


def test_checker_inexequible_status_superseded():
    checker = VigencyChecker()
    result = checker.check(document=_doc(status="inexequible"), article=None)
    assert result.status == "superseded"


def test_checker_article_modificado_por():
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article={
        "number": "1",
        "text": "El término es de tres días, modificado por el artículo 2 de la Ley 794 de 2003.",
    })
    assert result.status == "modified"
    assert result.evidence_source == "article_text_marker"
    assert "Ley 794" in result.superseded_by


def test_checker_article_derogado_por():
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article={
        "number": "2",
        "text": "Este artículo fue derogado por el artículo 100 de la Ley 1564 de 2012.",
    })
    assert result.status == "superseded"


def test_checker_article_substituido_por():
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article={
        "number": "3",
        "text": "Sustituido por el Decreto 019 de 2012.",
    })
    assert result.status == "superseded"


def test_checker_article_pendiente_document_status():
    """Estado 'pendiente' (información pendiente / aún no en vigor):
    document-level check → NO vigente."""
    checker = VigencyChecker()
    result = checker.check(document=_doc(status="pendiente"), article=None)
    assert result.status == "superseded"


def test_checker_no_evidence_is_uncertain():
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article={"number": "1", "text": ""})
    assert result.status == "uncertain"
    assert result.evidence_source == "no_evidence"


def test_checker_does_not_invent_vigency():
    """Artículo sin marcadores → vigente por metadatos, nunca inventado."""
    checker = VigencyChecker()
    result = checker.check(document=_doc(), article={
        "number": "4", "text": "Texto sin marcadores de modificación.",
    })
    assert result.status == "vigent"
    assert result.evidence_source == "document_metadata"


# ===== Fuentes oficiales — declarativas, sin conectividad simulada =====

def test_official_sources_catalog_is_declarative():
    """El catálogo NO inventa URLs ni simula conectividad: URL vacía =
    pendiente de integración real (honesto)."""
    from albra.knowledge.sources import COLOMBIA_OFFICIAL_SOURCES
    assert COLOMBIA_OFFICIAL_SOURCES, "catálogo vacío"
    for source in COLOMBIA_OFFICIAL_SOURCES.values():
        # Ninguna fuente declara una URL (no hay integración real aún).
        assert source.url == "", (
            f"Fuente {source.id} declara URL sin integración real: {source.url}"
        )


def test_sources_tiers_and_compliance():
    from albra.knowledge.schemas import SourceTier
    from albra.knowledge.sources import can_back_compliance
    assert can_back_compliance(SourceTier.S0_PRIMARY_SUPERIOR) is True
    assert can_back_compliance(SourceTier.S1_OFFICIAL) is True
    assert can_back_compliance(SourceTier.S2_ACADEMIC) is False
    assert can_back_compliance(SourceTier.S4_SECONDARY) is False


def test_ingestion_colombia_has_real_fetch_infrastructure():
    """ingestion_colombia SÍ tiene fetcher real (urllib) — infraestructura
    existente con URLs reales; no se afirma verificación en tiempo real
    (el fetch es bajo demanda y su cobertura depende de la fuente)."""
    from albra.knowledge.ingestion_colombia import OFFICIAL_SOURCES, IngestionCoordinator
    coordinator = IngestionCoordinator()
    assert coordinator._fetcher is not None  # fetcher real por defecto
    # Los registros declaran URLs de fuentes oficiales reales.
    assert "funcionpublica.gov.co" in OFFICIAL_SOURCES["gestor_normativo"]["url"]
