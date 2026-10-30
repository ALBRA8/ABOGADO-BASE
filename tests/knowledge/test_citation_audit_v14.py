"""Tests del CitationAuditor alineado al corpus canónico V1.4+V1.3 (v14).

Hallazgo 7 del cierre — diferenciación de garantías:
- EXTRACCIÓN: patrones de cita jurídica (incluye Decreto ahora).
- VALIDACIÓN DOCUMENTAL: documento + artículo existen en el corpus
  canónico (por number, por TITLE, o sentencia normalizada).
- FIDELIDAD SEMÁNTICA: solo el retracing literal queda demostrado
  (``literal_retraced``); una paráfrasis NUNCA se declara verificada.
- FAIL-CLOSED: ``validate_citation_direct`` para citas construidas por
  el engine; una cita no verificada bloquea la respuesta.
"""
from __future__ import annotations

import pytest

from albra.knowledge.citation_audit import Citation, CitationAuditor


@pytest.fixture
def auditor_v14():
    return CitationAuditor(corpus_version="v14")


# ===== Extracción =====

def test_extract_decreto_with_article(auditor_v14):
    """Nuevo patrón Decreto (el CST canónico es 'Decreto 2663 de 1950')."""
    cits = auditor_v14.extract_citations(
        "Según el Decreto 2663 de 1950, artículo 23, la jornada ordinaria es limitada."
    )
    decretos = [c for c in cits if c.document_name == "Decreto 2663 de 1950"]
    assert len(decretos) == 1
    assert decretos[0].article_number == "23"


# ===== Validación documental (v14) =====

def test_v14_validates_constitution_full_corpus(auditor_v14):
    """V1.4 tiene la Constitución COMPLETA (380 arts): art. 350 existe."""
    cits = [Citation(
        raw_text="artículo 350 de la Constitución",
        document_type="constitucion",
        document_name="Constitución Política de 1991",
        article_number="350",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 1 and len(u) == 0
    assert v[0].fidelity == "document_only"  # sin snippet: paráfrasis no demostrada


def test_v14_resolves_cst_by_title(auditor_v14):
    """El título 'Código Sustantivo del Trabajo' resuelve al doc cuyo
    number es 'Decreto 2663 de 1950' (índice por number Y title)."""
    cits = [Citation(
        raw_text="Código Sustantivo del Trabajo artículo 23",
        document_type="legislacion",
        document_name="Código Sustantivo del Trabajo",
        article_number="23",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 1, f"Debe resolver por título: u={u}"
    assert v[0].fidelity == "document_only"


def test_v14_resolves_sentencia_slash_form(auditor_v14):
    """'Sentencia T-001/2020' resuelve al doc v14 number 'T-001-2020'."""
    cits = [Citation(
        raw_text="Sentencia T-001/2020",
        document_type="jurisprudencia",
        document_name="Sentencia T-001/2020",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 1, f"Debe resolver la forma con slash: u={u}"


def test_v14_resolves_ley_100_v13(auditor_v14):
    """Ley 100/1993 vive en el corpus canónico vía V1.3 (12 docs)."""
    cits = [Citation(
        raw_text="Ley 100 de 1993",
        document_type="legislacion",
        document_name="Ley 100 de 1993",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 1


def test_v14_unknown_norm_unverified(auditor_v14):
    cits = [Citation(
        raw_text="Ley 9999 de 2099",
        document_type="legislacion",
        document_name="Ley 9999 de 2099",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 0 and len(u) == 1


def test_v14_rejected_document_still_rejected(auditor_v14):
    """Los documentos rechazados honestamente (V1.1) siguen rechazados."""
    cits = [Citation(
        raw_text="Sentencia C-251/2002",
        document_type="jurisprudencia",
        document_name="Sentencia C-251/2002",
    )]
    v, u, r = auditor_v14.validate_against_corpus(cits)
    assert len(v) == 0 and len(r) == 1


# ===== Fidelidad semántica =====

def test_fidelity_literal_retraced_with_real_snippet(auditor_v14):
    """Snippet literal del artículo → literal_retraced."""
    ok, fidelity, reason = auditor_v14.validate_citation_direct(
        document_name="Constitución Política de 1991",
        article_number="25",
        snippet=(
            "El trabajo es un derecho y una obligación social y goza, "
            "en todas sus modalidades, de la especial protección del Estado."
        ),
    )
    assert ok is True
    assert fidelity == "literal_retraced"


def test_fidelity_paraphrase_not_verified(auditor_v14):
    """REGRESIÓN hallazgo 7: una PARÁFRASIS no se declara verificada —
    el documento existe (document_only), la fidelidad NO queda demostrada."""
    ok, fidelity, _reason = auditor_v14.validate_citation_direct(
        document_name="Constitución Política de 1991",
        article_number="25",
        snippet="El Estado protege especialmente quien trabaja en Colombia.",
    )
    assert ok is True
    assert fidelity == "document_only"
    assert fidelity != "literal_retraced"


def test_fidelity_empty_snippet_document_only(auditor_v14):
    ok, fidelity, _reason = auditor_v14.validate_citation_direct(
        document_name="Constitución Política de 1991",
        article_number="25",
        snippet="",
    )
    assert ok is True
    assert fidelity == "document_only"


def test_citation_direct_nonexistent_article_blocks(auditor_v14):
    """Artículo inexistente en el documento → in_corpus=False (fail-closed)."""
    ok, fidelity, reason = auditor_v14.validate_citation_direct(
        document_name="Constitución Política de 1991",
        article_number="9999",
        snippet="",
    )
    assert ok is False
    assert fidelity == ""
    assert "9999" in reason


def test_citation_direct_external_document_blocks(auditor_v14):
    ok, fidelity, reason = auditor_v14.validate_citation_direct(
        document_name="Ley 1480 de 2011",
        article_number="1",
        snippet="",
    )
    assert ok is False
    assert "no está en el corpus" in reason


def test_citation_direct_nonexistent_document(auditor_v14):
    ok, _fidelity, _reason = auditor_v14.validate_citation_direct(
        document_name="Código Civil de Colombia",
        article_number="1602",
        snippet="",
    )
    assert ok is False


# ===== Corpus index shape =====

def test_v14_index_has_12_documents(auditor_v14):
    """Índice canónico: V1.4 (10) + leyes V1.3 vivas (2) = 12."""
    # number + title aliases existen; contar documentos ÚNICOS por entry
    unique_entries = set()
    for key, entry in auditor_v14._index.items():
        unique_entries.add(id(entry))
    assert len(unique_entries) == 12
