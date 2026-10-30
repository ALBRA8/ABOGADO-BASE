"""Tests de la Official Legal Source Layer (estados inequívocos).

La capa DEBE demostrar la diferencia entre SOURCE_REGISTERED,
SOURCE_FETCHABLE, SOURCE_VERIFIED y SOURCE_CURRENT con evidencia
(manifests reales con URL + HTTP status + SHA-256 + timestamp), nunca
por aserción.
"""
from __future__ import annotations

import hashlib

from albra.knowledge.official_sources import (
    OfficialSourceLayer,
    SourceFetchStatus,
    SourceVerificationRecord,
)


def _layer() -> OfficialSourceLayer:
    return OfficialSourceLayer()


def test_estados_son_inequivos_y_distintos():
    assert (
        SourceFetchStatus.SOURCE_REGISTERED
        != SourceFetchStatus.SOURCE_FETCHABLE
        != SourceFetchStatus.SOURCE_VERIFIED
        != SourceFetchStatus.SOURCE_CURRENT
    )


def test_fuentes_ingestadas_estan_verified():
    """Toda fuente con manifest real (v14_raw/v15_raw) es SOURCE_VERIFIED
    con HTTP 200 + hash + timestamp + al menos 1 página."""
    layer = _layer()
    verified = layer.by_status(SourceFetchStatus.SOURCE_VERIFIED)
    # 12 claves: 5 V1.4 (constitucion, cgp, l640, cpp, cst + sentencias) +
    # 11 V1.5 = al menos 11 distintas
    assert len(verified) >= 11
    for r in verified:
        assert r.http_status == 200
        assert len(r.raw_bytes_hash) == 64
        assert r.retrieval_timestamp
        assert r.pages >= 1


def test_fuentes_catalogadas_sin_evidencia_solo_registered():
    """El catálogo declarativo (sources.py) NO hereda VERIFIED sin evidencia."""
    layer = _layer()
    registered = layer.by_status(SourceFetchStatus.SOURCE_REGISTERED)
    assert registered, "el catálogo declarativo debe quedar REGISTERED"
    for r in registered:
        assert r.http_status == 0
        assert r.raw_bytes_hash == ""
        assert r.retrieval_timestamp == ""


def test_verificacion_independiente_del_concatenado():
    """El hash del registro se puede re-calcular desde disco (sin red)."""
    from pathlib import Path

    layer = _layer()
    rec = layer.get("codigo_civil")
    assert rec is not None
    base = Path("albra/knowledge/colombia/corpus_pilot/v15_raw/codigo_civil")
    combined = b""
    for p in sorted(base.glob("*.htm*")):
        combined += p.read_bytes()
    assert hashlib.sha256(combined).hexdigest() == rec.raw_bytes_hash


def test_reverify_sin_red_declarar_unreachable():
    """reverify contra una URL inalcanzable → SOURCE_UNREACHABLE (no simula)."""
    layer = _layer()
    rec = SourceVerificationRecord(
        source_key="fuente_inexistente_test",
        authority="Test",
        url="http://dominio-inexistente-albra-test.invalid/norma.htm",
        http_status=200,
        content_type="text/html",
        raw_bytes_hash="a" * 64,
        raw_bytes_size=10,
        retrieval_timestamp="2026-10-30T00:00:00+00:00",
        status=SourceFetchStatus.SOURCE_VERIFIED,
        notes={"first_page_hash": "a" * 64},
    )
    layer._records["fuente_inexistente_test"] = rec
    result = layer.reverify("fuente_inexistente_test", timeout=5)
    assert result == SourceFetchStatus.SOURCE_UNREACHABLE


def test_reverify_sin_url_error():
    layer = _layer()
    assert layer.reverify("fuente_que_no_existe") == SourceFetchStatus.SOURCE_ERROR


def test_stats_y_by_status():
    layer = _layer()
    stats = layer.stats()
    assert stats.get("SOURCE_VERIFIED", 0) >= 11
    assert stats.get("SOURCE_REGISTERED", 0) >= 1
    keys = layer.verified_source_keys()
    assert "codigo_civil" in keys
    assert "sentencia_T-760-2008" in keys
    # fuentes REGISTERED nunca aparecen como verificadas
    assert "suin_juriscol" not in keys
