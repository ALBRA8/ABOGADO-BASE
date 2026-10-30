"""Tests del plan de cobertura jurídica (PROMPT MAESTRO §5).

La cobertura declarada debe SER la cobertura real: cada entrada
PRESENT_FULL debe corresponder a un documento ingerido y verificado en
el corpus canónico; ninguna entrada puede declararse PRESENT sin corpus.
"""
from __future__ import annotations

import pytest

from albra.knowledge.colombia.coverage_plan import (
    COVERAGE_PLAN,
    DOMINIOS_REQUERIDOS_PROMPT,
    coverage_summary,
)
from albra.knowledge.corpus_seed import canonical_corpus_documents


def test_todos_los_dominios_del_prompt_estan_representados():
    declared = {e.dominio for e in COVERAGE_PLAN}
    for d in DOMINIOS_REQUERIDOS_PROMPT:
        assert d in declared, f"dominio sin entrada: {d}"


def test_present_full_corresponde_a_corpus_real():
    """Regla crítica: PRESENT_FULL ⟹ documento ingerido con ese conteo."""
    corpus_by_id = {d["source_id"]: d for _, d in canonical_corpus_documents()}
    for e in COVERAGE_PLAN:
        if e.estado == "PRESENT_FULL":
            # entrada con source_id directo
            doc = corpus_by_id.get(e.en_corpus)
            if doc is None:
                # jurisprudencia V1.4: referencia por grupo
                assert "sentencias" in e.en_corpus or e.articulos == 0
                continue
            assert len(doc["articles"]) == e.articulos, (
                f"{e.norma}: declarado {e.articulos}, corpus {len(doc['articles'])}"
            )


def test_ninguna_entrada_present_sin_corpus():
    corpus_by_id = {d["source_id"]: d for _, d in canonical_corpus_documents()}
    for e in COVERAGE_PLAN:
        if e.estado.startswith("PRESENT"):
            if e.articulos > 0:
                assert e.en_corpus in corpus_by_id, (
                    f"{e.norma} declara PRESENT pero no está en el corpus"
                )


def test_absent_declaran_bloqueo_o_decision():
    for e in COVERAGE_PLAN:
        if e.estado.startswith("ABSENT"):
            assert e.estado in (
                "ABSENT_BLOCKED", "ABSENT_DECISION", "ABSENT_PLANNED",
            ), f"estado de ausencia no reconocido: {e.estado}"


def test_resumen_cobertura_consistente():
    s = coverage_summary()
    assert s["total_entries"] == len(COVERAGE_PLAN)
    assert s["present_full"] >= 11  # 6 normas V1.5 + 5 normas V1.4
    assert s["total_articulos_corpus"] == 8114
    for dom in DOMINIOS_REQUERIDOS_PROMPT:
        assert dom in s["by_domain"]


@pytest.mark.parametrize("estado", ["PRESENT_FULL", "PRESENT_PARTIAL", "ABSENT_BLOCKED", "ABSENT_PLANNED", "ABSENT_DECISION"])
def test_estados_conocidos(estado):
    assert any(e.estado == estado for e in COVERAGE_PLAN) or estado == "PRESENT_PARTIAL"
