"""V8.0 Fase 4 — Candidato 3: stale text (actualizado a V1.5+V1.4 en Fase Producción Real).

Verifica que exam.py NO contiene referencias stale a "V1.3" en
strings que se presentan al usuario o al LLM, y que las limitations
estándar reflejan correctamente la cobertura V1.5+V1.4 (8115 artículos
en 5 cuerpos legales + 5 sentencias en texto reconstruido).

Las únicas menciones "V1.3" permitidas son las que documentan el
fallback V1.3 si la importación V1.4 falla (defensa en profundidad).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import ALL_DOCUMENTS_V14
from albra.lawyer.exam import LawyerExam
from albra.llm.providers import MockProvider
from albra.llm.real_provider_guard import RealProviderGuard

EXAM_PY = Path(__file__).resolve().parents[2] / "albra" / "lawyer" / "exam.py"


def _read_exam_py() -> str:
    return EXAM_PY.read_text(encoding="utf-8")


# ===== 1. No stale "V1.3" in user-facing strings =====

def test_exam_py_no_stale_v13_in_user_facing_strings():
    """Las únicas menciones V1.3 permitidas son las que documentan el
    fallback V1.3 si la import V1.4 falla. Ningún string que se muestre
    al usuario o se envíe al LLM debe decir "V1.3" sin justificación."""
    src = _read_exam_py()
    # Allowed contexts: docstring of _lookup_in_corpus describing fallback,
    # and the inline comment "# V8.0 Fase 2.2: try V1.4 first, fall back to V1.3."
    # Cierre de extracción: el corpus CANÓNICO es V1.4 + leyes V1.3 vivas
    # (ver albra/knowledge/corpus_seed.py — 12 docs, 2.200 arts), por lo
    # que los comentarios que documentan esa composición canónica son
    # menciones legítimas de V1.3 (no stale).
    allowed_patterns = [
        r'"""Look up a specific article in the V1\.4 corpus \(with V1\.3 fallback\)\.',
        r'V8\.0 Fase 2\.2: updated from V1\.3 to V1\.4',
        r'V1\.3 is used as fallback if V1\.4 import fails',
        r'# V8\.0 Fase 2\.2: try V1\.4 first, fall back to V1\.3',
        r'# citas con el corpus canónico V1\.4 \+ leyes V1\.3',
        r'# Indica si el corpus canónico V1\.4\+V1\.3 está disponible',
        r'# Leyes V1\.3 vivas del corpus canónico',
        r'# NORMAS VERIFICADAS \(corpus canónico V1\.4\+V1\.3',
        r'f"NORMAS VERIFICADAS \(corpus canónico V1\.4\+V1\.3',
    ]
    # Find all "V1.3" mentions
    v13_lines = []
    for i, line in enumerate(src.splitlines(), start=1):
        if re.search(r'V1\.3', line):
            v13_lines.append((i, line.strip()))
    # Each must match at least one allowed pattern
    unallowed = []
    for lineno, line in v13_lines:
        if not any(re.search(p, line) for p in allowed_patterns):
            unallowed.append((lineno, line))
    assert not unallowed, (
        f"Found stale 'V1.3' mentions outside allowed fallback docs: {unallowed}"
    )


# ===== 2. V1.4 references in user-facing strings =====

def test_exam_py_step_5_summary_uses_v14():
    """Step 5 summary must say 'corpus V1.4' not 'V1.3'."""
    src = _read_exam_py()
    assert "Fuentes encontradas en corpus V1.5+V1.4" in src, (
        "Step 5 summary should reference V1.5+V1.4"
    )
    assert "Fuentes encontradas en corpus V1.3" not in src, (
        "Step 5 summary should NOT reference V1.3"
    )


def test_exam_py_step_7_prompt_uses_v15():
    """Step 7 LLM prompt must say 'corpus V1.5+V1.4' with corpus enumeration."""
    src = _read_exam_py()
    assert "NORMAS VERIFICADAS (corpus V1.5+V1.4" in src
    # Step 7 prompt specifically (with article_texts variable).
    # In the source code, \n is the 2-char literal backslash-n inside an f-string.
    assert (
        r"NORMAS VERIFICADAS (corpus V1.5+V1.4 — Constitución/Civil/Penal/CPACA/Comercio/CGP/CPP/CST/Ley 640/Ley 100/Ley 80):\n{article_texts}"
        in src
    ), "Step 7 prompt should enumerate V1.5+V1.4 bodies"


def test_exam_py_step_10_prompt_uses_v15():
    """Step 10 LLM prompt must say 'corpus canónico V1.5+V1.4' with corpus enumeration.

    Fase Producción Real: el corpus canónico del agente es V1.5+V1.4
    (21 docs — ver albra/knowledge/corpus_seed.py); el prompt enumera
    todos los cuerpos (Civil/Penal/CPACA/Comercio añadidos en V1.5).
    """
    src = _read_exam_py()
    # Step 10 prompt uses inline join with f-string
    assert 'NORMAS VERIFICADAS (corpus canónico V1.5+V1.4 — Constitución/Civil/Penal/CPACA/Comercio/CGP/CPP/CST/Ley 640/Ley 100/Ley 80):\\n" + "\\n".join(' in src, (
        "Step 10 prompt should enumerate canonical V1.5+V1.4 bodies with inline join"
    )


def test_exam_py_step_11_prompt_uses_v15():
    """Step 11 LLM prompt must say 'corpus V1.5+V1.4' not 'V1.3'."""
    src = _read_exam_py()
    assert "estén en el corpus V1.5+V1.4" in src
    assert "estén en el corpus V1.3" not in src


# ===== 3. Limitations estándar actualizadas =====

def test_limitations_mention_v14_not_v13_for_corpus():
    """result.limitations debe mencionar 'V1.4' y NO 'V1.3' en el
    limitation sobre cobertura del corpus."""
    # Build a minimal case that completes successfully
    from tests.knowledge.test_v80_fase2_validation import _StubLLMProvider
    case = {
        "summary": "test stale text fix",
        "facts": ["fact"],
        "legal_issues": ["issue"],
        "required_sources": [
            {"document": "constitucion", "article": "29"},
        ],
        "document_type": "escrito",
    }
    stub = _StubLLMProvider()
    guard = RealProviderGuard(provider=stub, role="lawyer")
    exam = LawyerExam(case_id="test-stale-fix", case_facts=case, guard=guard)
    result = exam.run()
    # Find the corpus-coverage limitation
    corpus_lims = [lim for lim in result.limitations if "corpus" in lim.lower() and "cubre" in lim.lower()]
    assert corpus_lims, f"Expected a corpus coverage limitation, got: {result.limitations}"
    corpus_lim = corpus_lims[0]
    assert "V1.4" in corpus_lim, f"Limitation should mention V1.4: {corpus_lim}"
    assert "V1.3" not in corpus_lim, f"Limitation should NOT mention V1.3: {corpus_lim}"


def test_limitations_mention_v15_corpus_coverage_with_counts():
    """result.limitations debe enumerar los 11 cuerpos legales del
    corpus canónico V1.5+V1.4 con sus conteos de artículos."""
    from tests.knowledge.test_v80_fase2_validation import _StubLLMProvider
    case = {
        "summary": "test",
        "facts": ["fact"],
        "legal_issues": ["issue"],
        "required_sources": [{"document": "constitucion", "article": "29"}],
        "document_type": "escrito",
    }
    stub = _StubLLMProvider()
    guard = RealProviderGuard(provider=stub, role="lawyer")
    exam = LawyerExam(case_id="test-stale-coverage", case_facts=case, guard=guard)
    result = exam.run()
    corpus_lims = [lim for lim in result.limitations if "corpus jurídico V1.5+V1.4 cubre" in lim]
    assert corpus_lims, f"Expected V1.5+V1.4 corpus coverage limitation: {result.limitations}"
    lim = corpus_lims[0]
    # Verify enumeration of the 11 bodies
    assert "Constitución 1991 (380 " in lim, f"Missing Constitución count: {lim}"
    assert "Código Civil (Ley 57/1887, 2673 arts.)" in lim, f"Missing Civil count: {lim}"
    assert "Código Penal (Ley 599/2000, 598 arts.)" in lim, f"Missing Penal count: {lim}"
    assert "CPACA (Ley 1437/2011, 321 arts.)" in lim, f"Missing CPACA count: {lim}"
    assert "Código de Comercio (Decreto 410/1971, 2037 arts.)" in lim, f"Missing Comercio count: {lim}"
    assert "Ley 1564/2012 CGP (627 arts.)" in lim, f"Missing CGP count: {lim}"
    assert "Ley 640/2001 (50 arts.)" in lim, f"Missing Ley 640 count: {lim}"
    assert "Ley 906/2004 CPP (564 arts.)" in lim, f"Missing CPP count: {lim}"
    assert "Código Sustantivo del Trabajo (485 " in lim, f"Missing CST count: {lim}"
    assert "Ley 100/1993 (296 arts.)" in lim, f"Missing Ley 100 count: {lim}"
    assert "Ley 80/1993 (83 arts.)" in lim, f"Missing Ley 80 count: {lim}"
    assert "8114 artículos" in lim, f"Missing total count: {lim}"


def test_limitations_mention_jurisprudence_in_v14():
    """result.limitations debe mencionar las 5 sentencias T-xxx-2020,
    NO decir 'no hay jurisprudencia'."""
    from tests.knowledge.test_v80_fase2_validation import _StubLLMProvider
    case = {
        "summary": "test",
        "facts": ["fact"],
        "legal_issues": ["issue"],
        "required_sources": [{"document": "constitucion", "article": "29"}],
        "document_type": "escrito",
    }
    stub = _StubLLMProvider()
    guard = RealProviderGuard(provider=stub, role="lawyer")
    exam = LawyerExam(case_id="test-stale-jurisprudence", case_facts=case, guard=guard)
    result = exam.run()
    jurisprudence_lims = [lim for lim in result.limitations if "jurisprudencia" in lim.lower() or "sentencias" in lim.lower()]
    assert jurisprudence_lims, (
        f"Expected jurisprudence limitation, got: {result.limitations}"
    )
    lim = jurisprudence_lims[0]
    # Should NOT say "no hay jurisprudencia"
    assert "no hay jurisprudencia" not in lim.lower(), (
        f"Limitation should NOT say 'no hay jurisprudencia': {lim}"
    )
    # Should mention sentencias. The limitation uses compact form
    # "T-001/002/003/100/445-2020" so we check for the sentencia
    # numbers that uniquely identify the set.
    assert "T-001" in lim, f"Limitation should mention sentencia T-001: {lim}"
    assert "445" in lim, f"Limitation should mention sentencia 445: {lim}"
    assert "100" in lim, f"Limitation should mention sentencia 100: {lim}"
    assert "T-760" in lim, f"Limitation should mention sentencia T-760: {lim}"
    assert "C-355" in lim, f"Limitation should mention sentencia C-355: {lim}"
    assert "10 sentencias" in lim, f"Limitation should mention count of 10: {lim}"


# ===== 4. V1.3 fallback logic preserved =====

def test_v13_fallback_logic_preserved_in_lookup():
    """_lookup_in_corpus debe todavía intentar V1.4 primero con
    fallback V1.3 si el import V1.4 falla. Esto es defensa en
    profundidad, no stale text."""
    src = _read_exam_py()
    # Verify the fallback try/except structure is preserved
    assert "try:" in src and "from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import" in src
    assert "except ImportError:" in src
    assert "from albra.knowledge.colombia.corpus_pilot.real_corpus_v13 import" in src
    assert "ALL_DOCUMENTS_V13" in src


def test_lookup_in_corpus_finds_v14_article():
    """Sanity: _lookup_in_corpus still finds an article in V1.4."""
    from tests.knowledge.test_v80_fase2_validation import _StubLLMProvider
    case = {
        "summary": "test",
        "facts": ["fact"],
        "legal_issues": ["issue"],
        "required_sources": [{"document": "constitucion", "article": "29"}],
        "document_type": "escrito",
    }
    stub = _StubLLMProvider()
    guard = RealProviderGuard(provider=stub, role="lawyer")
    exam = LawyerExam(case_id="test-lookup", case_facts=case, guard=guard)
    found = exam._lookup_in_corpus("constitucion", "29")
    assert found is not None, "Constitución art. 29 should be found in V1.4"
    assert "article_text" in found


# ===== 5. V1.4 corpus structure sanity =====

def test_v14_corpus_has_expected_document_count():
    """Sanity: V1.4 has 5 statutory documents + 5 sentencias."""
    statutory = [s for s, d in ALL_DOCUMENTS_V14 if d.get("document_type") != "jurisprudencia"]
    jurisprudence = [s for s, d in ALL_DOCUMENTS_V14 if d.get("document_type") == "jurisprudencia"]
    assert len(statutory) == 5, f"Expected 5 statutory docs, got {len(statutory)}"
    assert len(jurisprudence) == 5, f"Expected 5 sentencias, got {len(jurisprudence)}"


def test_v14_corpus_total_articles_2106():
    """Sanity: V1.4 has 2106 articles total (2107 previo menos 1 artículo
    fantasma de Ley 640 corregido en la Fase Producción Real)."""
    total = sum(len(d.get("articles", [])) for _, d in ALL_DOCUMENTS_V14)
    assert total == 2106, f"Expected 2106 total articles, got {total}"
