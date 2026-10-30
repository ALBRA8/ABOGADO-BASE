"""Tests del motor de vigencia real — Fase Producción Real.

Cubre el hallazgo T2 de la auditoría: consultas históricas con fecha
usaban texto consolidado en silencio o abstenían espuriamente. Ahora:
  - fechas exactas → as_of exacto;
  - años de referencia → as_of aproximado DECLARADO;
  - identificación de normas ("Ley 100 de 1993") NO es fecha;
  - modificaciones posteriores a la fecha consultada → ABSTENCIÓN
    (cero autoridad fantasma — nunca texto consolidado como histórico);
  - artículos sin cambios posteriores → respuesta con contexto temporal.
"""
from __future__ import annotations

from datetime import date

import pytest

from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import (
    ALL_DOCUMENTS_V14,
)
from albra.knowledge.query_classifier import LegalQueryClassifier
from albra.knowledge.temporal import (
    extract_modification_years,
    parse_temporal_reference,
)

# ===== parse_temporal_reference =====

def test_fecha_exacta_parseada():
    d, p = parse_temporal_reference("¿Qué decía el artículo 25 de la Constitución el 15 de marzo de 2018?")
    assert (d, p) == (date(2018, 3, 15), "exact")


def test_hechos_de_anio_aproximado():
    d, p = parse_temporal_reference("¿Esta norma estaba vigente cuando ocurrieron los hechos de 2015?")
    assert (d, p) == (date(2015, 12, 31), "approx")


def test_identificacion_de_norma_NO_es_fecha():
    d, p = parse_temporal_reference("¿Qué dice la Ley 100 de 1993 sobre pensiones?")
    assert d is None and p == ""


def test_consulta_sin_fecha():
    d, p = parse_temporal_reference("¿Qué dice el artículo 25 de la Constitución?")
    assert d is None and p == ""


def test_fecha_decreto_410_no_es_temporal():
    d, p = parse_temporal_reference("¿Qué establece el artículo 871 del Decreto 410 de 1971?")
    assert d is None and p == ""


# ===== extract_modification_years (marcadores REALES del corpus) =====

def _cst_article(n: str) -> str:
    for _, d in ALL_DOCUMENTS_V14:
        if d["source_id"] == "codigo_sustantivo_trabajo_v14":
            return next(a["text"] for a in d["articles"] if a["number"] == n)
    raise AssertionError("CST no encontrado")


def test_cst_art23_subrogado_tiene_modificaciones_reales():
    """El art. 23 del CST está subrogado: el texto REAL contiene los
    marcadores con la ley modificatoria (ya no truncado)."""
    text = _cst_article("23")
    assert len(text) > 500  # texto completo (antes 48 chars por el bug)
    mods = extract_modification_years(text)
    assert mods, "el texto subrogado debe declarar su ley modificatoria"
    assert all(m["anio_ley"] >= 1950 for m in mods)


def test_articulo_sin_modificaciones_no_declara_cambios():
    mods = extract_modification_years("Texto sin ningún marcador de cambio posterior.")
    assert mods == []


# ===== clasificador =====

def test_clasificador_fecha_exacta_produce_as_of_exacto():
    c = LegalQueryClassifier()
    r = c.classify("¿Qué decía el artículo 25 de la Constitución el 15 de marzo de 2018?")
    assert r.temporal_hint == "as_of:2018-03-15"
    assert r.temporal_precision == "exact"


def test_clasificador_hechos_produce_as_of_aprox():
    c = LegalQueryClassifier()
    r = c.classify("¿Esta norma estaba vigente cuando ocurrieron los hechos de 2015?")
    assert r.temporal_hint == "as_of:2015-12-31"
    assert r.temporal_precision == "approx"


def test_clasificador_norma_identificada_no_produce_as_of():
    c = LegalQueryClassifier()
    r = c.classify("¿Qué dice la Ley 100 de 1993 sobre pensiones?")
    assert not r.temporal_hint.startswith("as_of")


# ===== engine E2E: guard histórico =====

@pytest.mark.asyncio
async def test_consulta_historica_articulo_sin_cambios_responde_con_contexto():
    """CC art. 1602 (sin marcadores posteriores) el 15-03-2018 → respuesta
    con evidencia + bloque de CONTEXTO TEMPORAL (nunca silencio)."""
    from albra.knowledge.corpus_seed import build_seeded_retriever
    from albra.knowledge.legal_engine import LegalKnowledgeEngine

    retriever, report = await build_seeded_retriever()
    try:
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        r = await engine.query(
            "¿Qué decía el artículo 1602 del Código Civil el 15 de marzo de 2018?"
        )
        assert r.abstention is False, r.abstention_reason
        blocks_text = " ".join(b.text for b in r.blocks)
        assert "CONTEXTO TEMPORAL" in blocks_text
        assert "2018-03-15" in blocks_text
        assert "(precisión: exact)" in blocks_text
        await engine.shutdown()
    finally:
        await retriever.provider.shutdown()


@pytest.mark.asyncio
async def test_consulta_historica_articulo_modificado_despues_abstiene():
    """CST art. 23 (subrogado por leyes posteriores) consultado a 2010 →
    ABSTENCIÓN explícita: el texto consolidado NO es la versión de 2010."""
    from albra.knowledge.corpus_seed import build_seeded_retriever
    from albra.knowledge.legal_engine import LegalKnowledgeEngine

    mods = extract_modification_years(_cst_article("23"))
    latest_year = max(int(m["fecha_efectiva"][:4]) for m in mods)
    as_of_year = latest_year - 5  # con seguridad ANTES de la modificación

    retriever, _ = await build_seeded_retriever()
    try:
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        r = await engine.query(
            f"¿Qué decía el artículo 23 del Código Sustantivo del Trabajo cuando ocurrieron los hechos de {as_of_year}?"
        )
        assert r.abstention is True
        assert "cambió DESPUÉS de la fecha consultada" in (r.abstention_reason or "")
        assert r.needs_hitl is True
        await engine.shutdown()
    finally:
        await retriever.provider.shutdown()


@pytest.mark.asyncio
async def test_consulta_as_of_anterior_a_la_norma_abstiene():
    """Constitución consultada a 1800: fuera del rango temporal → 0 hits
    → abstención de la política normal (no se inventa)."""
    from albra.knowledge.corpus_seed import build_seeded_retriever
    from albra.knowledge.legal_engine import LegalKnowledgeEngine

    retriever, _ = await build_seeded_retriever()
    try:
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        r = await engine.query(
            "¿Qué decía el artículo 25 de la Constitución el 15 de marzo de 1800?"
        )
        assert r.abstention is True
        await engine.shutdown()
    finally:
        await retriever.provider.shutdown()
