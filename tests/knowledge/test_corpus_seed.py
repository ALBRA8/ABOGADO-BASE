"""Pruebas de la migración de conocimiento jurídico (DESPACHO → ABOGADO-BASE).

Demuestran la ruta REAL del conocimiento (no "el corpus está en el repo"):

    CORPUS EN DISCO → INGESTIÓN → RETRIEVAL → LEGAL KNOWLEDGE ENGINE
    → EVIDENCE/PROVENANCE → RESPUESTA CON CITA

Cobertura:
    A. Independencia  → tests/test_knowledge_independence.py
    B. Conocimiento   → test_seed_carga_corpus_canonico
    C. Retrieval      → test_retrieval_recupera_articulo_real
    D. Provenance     → test_provenance_trazable (hashes + fuente + URL)
    E. Citas          → test_engine_e2e_respuesta_con_citas
    F. Vigencia       → cubierta por tests/knowledge (corpus V1.4) — sigue igual
    G. Norm refs      → cubierta por tests/knowledge/test_v80_fase3* — sigue igual
    H. LawyerExam     → cubierto por tests/lawyer — corpus V1.4 intacto
    I. CI             → lint + tests + clean-room (workflow existente)
"""
from __future__ import annotations

import hashlib

import pytest

from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import ALL_DOCUMENTS_V14
from albra.knowledge.corpus_seed import (
    CORPUS_VERSION,
    build_seeded_retriever,
    canonical_corpus_documents,
    seed_sync,
    verify_corpus_hashes,
)
from albra.knowledge.legal_engine import LegalKnowledgeEngine
from albra.knowledge.retrieval import RetrievalQuery

# ----------------------------------------------------------------------
# B. Conocimiento — el corpus migrado está disponible para el engine
# ----------------------------------------------------------------------


def test_hashes_del_corpus_verificados():
    """Cada documento canónico: sha256(reconstructed_text) == hash registrado."""
    mismatched = verify_corpus_hashes()
    assert mismatched == [], f"hashes inválidos: {mismatched}"


def test_seed_carga_corpus_canonico():
    """La siembra ingesta los 12 documentos canónicos sin rechazos."""
    report = seed_sync()
    assert report.corpus_version == CORPUS_VERSION
    assert report.ingested == 12, f"esperados 12 documentos, sembrados {report.ingested}"
    assert report.skipped_hash_mismatch == []
    assert report.rejected == []
    stats = report.stats
    assert stats["norms"] >= 7          # Constitución + 4 leyes/códigos V1.4 + 2 leyes V1.3
    assert stats["articles"] >= 2000    # 2083 artículos reales
    assert stats["jurisprudence"] == 5  # 5 sentencias reales Corte Constitucional


def test_corpus_canonico_sin_duplicar_normas():
    """Regla anti-duplicación: la misma norma no aparece dos veces."""
    docs = canonical_corpus_documents()
    source_ids = [d["source_id"] for _, d in docs]
    assert len(source_ids) == len(set(source_ids))
    # La Constitución V1.1/V1.3 (subconjunto) NO se siembra: la V1.4 la subsume.
    assert "const_1991_real_v11" not in source_ids
    assert "const_1991_real_v13" not in source_ids
    assert "constitucion_v14" in source_ids


def test_tipos_mapeados_con_provenance_original():
    """El tipo original del corpus se conserva en la provenance indexada."""
    report = seed_sync()
    por_id = {d["source_id"]: d for d in report.documents}
    cst = por_id["codigo_sustantivo_trabajo_v14"]
    assert cst["document_type"] == "codigo"               # tipo del esquema
    assert cst["corpus_document_type"] == "codigo_sustantivo"  # original conservado
    sent = por_id["sentencia_T-001-2020_v14"]
    assert sent["document_type"] == "sentencia"
    assert sent["corpus_document_type"] == "jurisprudencia"


@pytest.mark.asyncio
async def test_boot_del_engine_trae_corpus_no_provider_vacio():
    """build_seeded_retriever entrega un retriever CON conocimiento."""
    retriever, report = await build_seeded_retriever()
    try:
        assert report.ingested == 12
        stats = retriever.provider.stats()
        assert stats["articles"] >= 2000
    finally:
        await retriever.provider.shutdown()


# ----------------------------------------------------------------------
# C. Retrieval — una consulta jurídica real recupera conocimiento
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieval_recupera_articulo_real():
    """Consulta exacta por artículo → texto real del corpus migrado."""
    retriever, _report = await build_seeded_retriever()
    try:
        rq = RetrievalQuery(
            query_text="derecho a la vida",
            query_type="exact",
            norm_number="Constitución Política de 1991",
            article_number="11",
            jurisdiction="CO",
        )
        res = await retriever.retrieve(rq)
        assert res.total_found > 0
        top = res.candidates[0]
        assert "inviolable" in top.snippet.lower()
        # D. Provenance: trazabilidad hacia la fuente
        assert top.provenance.get("source_url", "").startswith("http")
        assert top.provenance.get("content_hash")
        assert top.source_tier is not None
    finally:
        await retriever.provider.shutdown()


# ----------------------------------------------------------------------
# E. Citas + D. Provenance — E2E del knowledge path completo
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_e2e_respuesta_con_citas_y_provenance():
    """Pregunta → engine → retrieval → corpus → cita con provenance."""
    retriever, _report = await build_seeded_retriever()
    try:
        engine = LegalKnowledgeEngine(retriever=retriever)
        await engine.startup()
        resp = await engine.query(
            "¿Qué establece el artículo 11 de la Constitución Política "
            "sobre el derecho a la vida?"
        )
        assert resp.abstention is False
        assert resp.query_type == "consulta_normativa"
        assert resp.blocks, "la respuesta debe tener bloques con contenido"
        block = resp.blocks[0]
        assert "inviolable" in block.text.lower()
        assert block.citations, "el bloque debe citar la fuente"
        cita = block.citations[0]
        assert cita.source_url.startswith("http")       # fuente oficial trazable
        assert cita.content_hash                         # hash del contenido
        await engine.shutdown()
    finally:
        await retriever.provider.shutdown()


# ----------------------------------------------------------------------
# D. Provenance — raw bytes V1.4 en disco con manifest verificable
# ----------------------------------------------------------------------


def test_raw_bytes_v14_preservados_en_disco():
    """V1.4 preserva raw_bytes + manifest con hashes en el repo del abogado."""
    import json
    from pathlib import Path

    raw_dir = Path(ALL_DOCUMENTS_V14[0][1].get("_raw_dir", "")) if ALL_DOCUMENTS_V14[0][1].get("_raw_dir") else None
    if raw_dir is None:
        from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import V14_RAW_DIR
        raw_dir = V14_RAW_DIR
    manifest_path = raw_dir / "constitucion_1991" / "manifest.json"
    assert manifest_path.exists(), "manifest de la Constitución debe estar en el repo del abogado"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest, "manifest con páginas capturadas"
    page = manifest[0]
    assert page["url"].startswith("http")
    assert page["raw_bytes_hash"]
    assert page["retrieval_timestamp"]
    # El fichero crudo existe y su hash coincide con el manifest
    raw_file = raw_dir / "constitucion_1991" / page["cached_at"]
    assert raw_file.exists()
    assert hashlib.sha256(raw_file.read_bytes()).hexdigest() == page["raw_bytes_hash"]


def test_corpus_v14_estadisticas_coherentes():
    """V14_STATS declara 5 documentos normativos + 5 sentencias (2083 arts)."""
    from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import V14_STATS

    assert V14_STATS["v14_documents"] == 5          # 5 documentos normativos V1.4
    assert V14_STATS["v14_total_articles"] == 2107  # artículos reales V1.4
    assert V14_STATS["v14_sentencias"] == 5         # 5 sentencias reales CC
    assert V14_STATS["v14_provenance_status_default"] == "VERIFIED"
    assert V14_STATS["v14_raw_bytes_preserved"] is True
