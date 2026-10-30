"""Tests de descubrimiento de problemas jurídicos y propuesta de fuentes.

Hallazgo 5 (P1) del cierre — autonomía de LawyerExam:
- El agente PUEDE proponer problemas jurídicos a partir de los hechos.
- El agente PUEDE proponer normas/jurisprudencia a investigar.
- Toda fuente propuesta se comprueba contra el corpus (pasos 5-6).
- Una fuente no encontrada queda EXPRESAMENTE sin verificar.
- El agente NO inventa artículos, sentencias ni datos del caso.
- Si la evidencia es insuficiente, se abstiene (regresión V7.0).
"""
from __future__ import annotations

import pytest

from albra.lawyer.exam import LawyerExam
from albra.lawyer.issue_discovery import (
    discover_domains,
    discover_legal_issues,
    propose_required_sources,
)
from albra.llm.providers import MockProvider
from albra.llm.real_provider_guard import RealProviderGuard


@pytest.fixture
def guard():
    return RealProviderGuard(provider=MockProvider(), role="lawyer")


LABORAL_CASE = {
    "summary": "Despido sin causa de trabajadora",
    "facts": [
        "El empleador despidió a la trabajadora sin causa justa.",
        "No se pagaron las prestaciones sociales ni las cesantías.",
    ],
    "documents": ["contrato de trabajo a término indefinido"],
    "uncertainties": ["fecha exacta del despido"],
    "document_type": "demanda laboral",
}


# ===== issue_discovery (unitario) =====

def test_discover_domains_laboral():
    domains = discover_domains(LABORAL_CASE)
    assert "laboral" in domains


def test_discover_legal_issues_proposes_from_facts():
    issues = discover_legal_issues(LABORAL_CASE)
    assert issues
    assert all(i["proposed_by_agent"] is True for i in issues)
    assert any("Código Sustantivo del Trabajo" in i["issue"] for i in issues)
    # Basis: derivada de hechos declarados (no inventada).
    assert all(i["basis"] for i in issues)


def test_discover_no_issues_from_generic_facts():
    """Hechos genéricos sin contenido jurídico → sin propuestas."""
    issues = discover_legal_issues({"facts": ["fact 1"], "summary": "no issues"})
    assert issues == []


def test_propose_sources_marks_unverified():
    sources = propose_required_sources(LABORAL_CASE)
    assert sources
    assert all(s["proposed_by_agent"] is True for s in sources)
    assert all(s["verified"] is False for s in sources), (
        "Una fuente propuesta nace SIN VERIFICAR hasta contrastar con corpus"
    )
    # La propuesta laboral mapea al corpus canónico (slug del corpus,
    # resolvible por los aliases de _lookup_in_corpus).
    assert any(s["document"] == "codigo_sustantivo_trabajo" for s in sources)


def test_propose_sources_with_specific_article_from_facts():
    case = {
        "summary": "Consulta constitucional",
        "facts": ["El due process requirement is at stake"],
        "documents": ["El debido proceso se rige por el artículo 29 de la Constitución Política"],
    }
    sources = propose_required_sources(case)
    constitution_sources = [s for s in sources if s["document"] == "constitucion"]
    assert constitution_sources, f"No propuso constitución: {sources}"
    assert any(s["article"] == "29" for s in constitution_sources)


def test_propose_sources_never_invents_articles():
    """Sin artículo citado en los hechos → propuesta a nivel documento
    (article=''), NUNCA un artículo inventado."""
    sources = propose_required_sources(LABORAL_CASE)
    for s in sources:
        if s["article"]:
            # Solo puede proponer artículos citados explícitamente en los hechos
            assert any("artícul" in f.lower() or "articulo" in f.lower() for f in LABORAL_CASE["facts"])


# ===== Integración con LawyerExam (12 pasos) =====

def test_exam_proposes_issues_and_sources(guard):
    """Caso SIN issues ni fuentes declaradas → el agente propone y el
    flujo llega a paso 6 con la fuente verificada contra corpus."""
    case = dict(LABORAL_CASE)
    exam = LawyerExam(case_id="disc-1", case_facts=case, guard=guard)
    result = exam.run()
    step3 = next(s for s in result.steps if s.step_number == 3)
    ev3 = step3.evidence[0]
    assert ev3["proposed_by_agent"] is True
    assert ev3["items"], "Sin propuestas de issues"
    assert "propuestos por el agente" in step3.summary.lower()
    step4 = next(s for s in result.steps if s.step_number == 4)
    ev4 = step4.evidence[0]
    assert ev4["proposed_by_agent"] is True
    step5 = next(s for s in result.steps if s.step_number == 5)
    assert step5.status == "ok"
    assert any(e["type"] == "found_in_corpus" for e in step5.evidence)
    step6 = next(s for s in result.steps if s.step_number == 6)
    assert step6.status == "ok"
    assert result.citations_verified
    # Limitación registrada: propuestas requieren revisión humana.
    assert any("propuestos" in lim for lim in result.limitations)


def test_exam_proposed_source_not_in_corpus_stays_unverified(guard):
    """Fuente propuesta de dominio SIN documento en corpus → expresamente
    SIN VERIFICAR (no se oculta)."""
    case = {
        "summary": "Caso tributario",
        "facts": ["La entidad cobró un impuesto aduanero inusual"],
        "uncertainties": [],
    }
    exam = LawyerExam(case_id="disc-2", case_facts=case, guard=guard)
    result = exam.run()
    if result.overall_status == "ABSTAINED" and not any(
        s.step_number == 5 for s in result.steps
    ):
        # Sin dominio detectable → abstención temprana (correcto).
        pytest.skip("Caso sin dominio detectable — abstención correcta")
    step5 = next(s for s in result.steps if s.step_number == 5)
    not_found = [e for e in step5.evidence if e["type"] == "not_in_corpus"]
    if not_found:
        assert all(e.get("sin_verificar") is True for e in not_found)
        assert any(e.get("proposed_by_agent") for e in not_found)


def test_exam_generic_case_still_abstains(guard):
    """REGRESIÓN V7.0: hechos genéricos sin contenido jurídico → ABSTAINED."""
    case = {
        "summary": "no issues",
        "facts": ["fact 1"],
        "legal_issues": [],
        "required_sources": [],
    }
    exam = LawyerExam(case_id="disc-3", case_facts=case, guard=guard)
    result = exam.run()
    assert result.overall_status == "ABSTAINED"


def test_exam_declared_issues_take_precedence(guard):
    """Los issues declarados por el caso prevalecen (comportamiento V7.0)."""
    case = {
        "summary": "declared",
        "facts": ["El empleador despidió al trabajador"],
        "legal_issues": ["issue declarado por el caso"],
        "required_sources": [{"document": "constitucion", "article": "28"}],
    }
    exam = LawyerExam(case_id="disc-4", case_facts=case, guard=guard)
    result = exam.run()
    step3 = next(s for s in result.steps if s.step_number == 3)
    ev3 = step3.evidence[0]
    assert ev3["proposed_by_agent"] is False
    assert ev3["items"] == ["issue declarado por el caso"]
    assert result.citations_verified, "fuente declarada y en corpus debe verificar"


def test_exam_uses_canonical_v14_auditor(guard):
    """El auditor del examen valida contra el corpus canónico (hallazgo 7)."""
    case = {"summary": "s", "facts": ["f"], "legal_issues": ["i"],
            "required_sources": [{"document": "constitucion", "article": "350"}]}
    exam = LawyerExam(case_id="disc-5", case_facts=case, guard=guard)
    assert exam.citation_auditor.corpus_version == "v14"
    result = exam.run()
    # Art. 350 NO está en V1.1 (12 arts) pero SÍ en V1.4 (380 arts).
    assert any(
        v["document"] == "constitucion" and v["article"] == "350"
        for v in result.citations_verified
    ), f"Art. 350 debe verificar contra V1.4: {result.citations_unverified}"


def test_exam_preserves_guarantees(guard):
    """Reglas inviolables intactas: RealProviderGuard + AdversarialValidator
    + abstención con evidencia insuficiente."""
    # MockProvider → BLOCKED (guard intacto).
    case = dict(LABORAL_CASE)
    exam = LawyerExam(case_id="disc-6", case_facts=case, guard=guard)
    result = exam.run()
    assert result.overall_status in ("BLOCKED", "ABSTAINED"), (
        f"MockProvider no puede producir SUCCESS: {result.overall_status}"
    )
    # AdversarialValidator sigue referenciado en los pasos 7/11.
    import inspect

    from albra.lawyer import adversarial_validation  # noqa: F401
    src = inspect.getsource(LawyerExam)
    assert "AdversarialValidator" in src
