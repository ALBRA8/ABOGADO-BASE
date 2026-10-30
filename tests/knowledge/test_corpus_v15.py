"""Tests del corpus V1.5 — expansión de cobertura jurídica real.

Verifica que la expansión (Código Civil, Penal, CPACA, Comercio, Ley 100
completa, Ley 80 completa + 5 sentencias emblemáticas) mantiene las
disciplinas del corpus canónico: hashes verificables, provenance oficial,
regla anti-duplicación y capacidad de respuesta con citas reales.
"""
from __future__ import annotations

import hashlib

import pytest

from albra.knowledge.colombia.corpus_pilot.real_corpus_v15 import (
    ALL_DOCUMENTS_V15,
    V15_STATS,
)
from albra.knowledge.corpus_seed import (
    canonical_corpus_documents,
    verify_corpus_hashes,
)


def _doc(source_id: str) -> dict:
    for _, d in ALL_DOCUMENTS_V15:
        if d["source_id"] == source_id:
            return d
    raise AssertionError(f"documento no encontrado: {source_id}")


# ===== Estructura =====

def test_v15_tiene_11_documentos():
    assert len(ALL_DOCUMENTS_V15) == 11
    assert V15_STATS["v15_documents"] == 6
    assert V15_STATS["v15_sentencias"] == 5


def test_v15_articulos_totales():
    # 2673 civil + 598 penal + 321 cpaca + 2037 comercio + 296 l100 + 83 l80
    assert V15_STATS["v15_total_articles"] == 6008


def test_v15_provenance_verificada():
    assert V15_STATS["v15_provenance_verified_count"] == 11
    for _, d in ALL_DOCUMENTS_V15:
        assert d["provenance_status"] == "VERIFIED"
        prov = d["provenance"].as_dict()
        sc = prov["source_capture"]
        assert sc["http_status"] == 200, d["source_id"]
        assert sc["raw_bytes_hash"], d["source_id"]
        assert sc["retrieval_method"] == "urllib"


def test_v15_hashes_reconstruccion_verificables():
    """sha256(reconstructed_text) == reconstructed_text_hash por documento."""
    for _, d in ALL_DOCUMENTS_V15:
        text = d["reconstructed_text"]
        expected = d["reconstructed_text_hash"]
        assert expected, d["source_id"]
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == expected, (
            d["source_id"]
        )


def test_v15_verificacion_canonica_incluye_v15():
    """canonical_corpus_documents() = V1.5 (11) + V1.4 (10) = 21, sin dupes."""
    docs = canonical_corpus_documents()
    ids = [d["source_id"] for _, d in docs]
    assert len(ids) == 21
    assert len(ids) == len(set(ids))
    verify = verify_corpus_hashes()
    assert verify == []


def test_v15_fuentes_oficiales_reales():
    """Las URLs provienen de las fuentes oficiales reales (no inventadas)."""
    for _, d in ALL_DOCUMENTS_V15:
        url = d["source_url"]
        assert (
            "secretariasenado.gov.co" in url
            or "corteconstitucional.gov.co" in url
        ), url


# ===== Cobertura por dominio (artículos clave REALES del texto) =====

@pytest.mark.parametrize(
    ("source_id", "article", "fragmento"),
    [
        # CIVIL: art. 1602 — contrato es ley para las partes
        ("codigo_civil_v15", "1602", "contrato"),
        # PENAL: art. 32 — favorabilidad... usamos art. 29 (concurso)
        ("codigo_penal_v15", "29", ""),
        # CPACA: art. 2 — naturaleza
        ("cpaca_ley_1437_2011_v15", "2", "procedimiento"),
        # COMERCIO: art. 1 — comerciantes
        ("codigo_comercio_v15", "1", ""),
        # SEGURIDAD SOCIAL: art. 1 — creación del sistema
        ("ley_100_1993_v15", "1", "seguridad social"),
        # CONTRATACIÓN: art. 1 — objeto
        ("ley_80_1993_v15", "1", ""),
    ],
)
def test_v15_articulos_clave_presentes(source_id, article, fragmento):
    d = _doc(source_id)
    nums = {a["number"] for a in d["articles"]}
    assert article in nums, f"{source_id} no contiene art. {article}"
    if fragmento:
        art = next(a for a in d["articles"] if a["number"] == article)
        assert fragmento.lower() in art["text"].lower()


def test_v15_sufijos_letra_capturados():
    """Ley 599 tiene artículos con sufijo (38A, 188-A...): deben existir."""
    d = _doc("codigo_penal_v15")
    nums = [a["number"] for a in d["articles"]]
    lettered = [n for n in nums if not n.isdigit()]
    assert len(lettered) >= 100, f"sufijos insuficientes: {len(lettered)}"
    assert "38A" in nums or "38a".upper() in [n.upper() for n in nums]


def test_v15_sentencias_emblematicas_texto_real():
    t760 = _doc("sentencia_T-760-2008_v15")
    assert "T-760" in t760["reconstructed_text"] or "T-760" in t760["title"]
    assert len(t760["reconstructed_text"]) > 5000  # sentencia real extensa
    c355 = _doc("sentencia_C-355-2006_v15")
    assert len(c355["reconstructed_text"]) > 5000


# ===== Integración con el motor =====

@pytest.mark.asyncio
async def test_engine_responde_civil_1602_con_evidencia():
    """Consulta clásica antes-imposible: Código Civil art. 1602 ahora
    se responde con evidencia real del corpus (fidelidad verificada)."""
    from albra.knowledge.corpus_seed import build_seeded_retriever
    from albra.knowledge.legal_engine import LegalKnowledgeEngine

    retriever, report = await build_seeded_retriever()
    try:
        assert report.ingested == 21
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        r = await engine.query(
            "¿Qué establece el artículo 1602 del Código Civil sobre los contratos?"
        )
        assert r.abstention is False
        assert r.citation_audit["all_verified"] is True
        assert any(
            "1602" in c.citation_text for c in _iter_citations(r)
        ), "la cita al art. 1602 debe aparecer"
        await engine.shutdown()
    finally:
        await retriever.provider.shutdown()


def _iter_citations(response):
    for b in response.blocks:
        for c in getattr(b, "citations", []) or []:
            yield c
