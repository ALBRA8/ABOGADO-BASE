"""RÚBRICA DE ABOGADO — evaluación objetiva de respuestas jurídicas.

Fase Producción Real (PROMPT §17): mide 14 dimensiones sobre el
resultado estructurado del agente y aplica una regla de absolución
cero:

    hallucinated legal authority  ⟹  FAIL total de la evaluación.

Las dimensiones se puntúan 0/0.5/1 con evidencia estructurada
(abstención, citation_audit, legal_analysis, conflictos, contexto
temporal, needs_hitl). El veredicto global es:
  READY (≥0.75 y sin FAIL) / CONDITIONAL (≥0.5) / FAIL.
La rúbrica NO reemplaza la revisión humana: es una medición objetiva
para la batería de casos y la regresión adversarial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DIMENSIONS = (
    "issue_identification",
    "fact_extraction",
    "missing_facts",
    "applicable_law",
    "legal_validity",
    "jurisprudence",
    "citation_accuracy",
    "source_provenance",
    "reasoning",
    "counterarguments",
    "risk_detection",
    "uncertainty",
    "abstention",
    "human_escalation",
)


@dataclass
class RubricResult:
    scores: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    hallucinated_authority: bool = False
    verdict: str = "FAIL"  # READY | CONDITIONAL | FAIL

    @property
    def mean(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scores": self.scores,
            "mean": round(self.mean, 3),
            "hallucinated_authority": self.hallucinated_authority,
            "verdict": self.verdict,
            "evidence_keys": sorted(self.evidence.keys()),
        }


def evaluate_legal_response(response: dict[str, Any]) -> RubricResult:
    """Evalúa una respuesta del agente (dict) contra la rúbrica.

    ``response`` puede ser el dict de ``agent.process(...)`` o un
    ``LegalResponse`` convertido. Campos usados (todos estructurados):
    abstention, abstention_reason, citation_audit, legal_analysis,
    conflicts, needs_hitl, blocks, temporal hints.
    """
    scores: dict[str, float] = {}
    evidence: dict[str, Any] = {}

    audit = response.get("citation_audit") or {}
    analysis = response.get("legal_analysis") or {}
    blocks = response.get("blocks") or []
    abstention = bool(response.get("abstention"))

    # 1) Autoridad jurídica fantasma — regla de absolución cero
    hallucinated = False
    if audit and audit.get("executed"):
        hallucinated = bool(audit.get("unverified", 0) > 0 and not abstention)
    elif not audit and not abstention and blocks:
        # respuesta sin auditoría de citas y sin abstención: no demostrable
        hallucinated = False  # el engine SIEMPRE audita pre-reveal; si el dict no lo trae, no se puede afirmar
        evidence["citation_audit_missing"] = True

    # 2) Dimensiones
    scores["issue_identification"] = _score_list(analysis.get("problemas_juridicos"))
    scores["fact_extraction"] = _score_list(analysis.get("hechos_declarados"))
    scores["missing_facts"] = _score_list(analysis.get("hechos_faltantes"), allow_empty_good=False)
    scores["applicable_law"] = _score_list(analysis.get("normas_aplicables"))
    scores["legal_validity"] = 1.0 if audit.get("executed") else (0.5 if abstention else 0.0)
    jurisprudencia = analysis.get("jurisprudencia_pertinente") or []
    scores["jurisprudencia"] = 1.0 if jurisprudencia else (0.5 if abstention else 0.0)
    fidelity = audit.get("fidelity") or {}
    scores["citation_accuracy"] = (
        1.0 if fidelity.get("literal_retraced") else (0.5 if fidelity.get("document_only") else (0.5 if abstention else 0.0))
    )
    scores["source_provenance"] = 1.0 if audit.get("corpus_version") else (0.5 if abstention else 0.0)
    scores["reasoning"] = 1.0 if analysis.get("argumentos") else (0.5 if abstention else 0.0)
    scores["counterarguments"] = _score_list(analysis.get("contraargumentos"), allow_empty_good=False)
    scores["risk_detection"] = _score_list(analysis.get("riesgos"), allow_empty_good=False)
    scores["uncertainty"] = 1.0 if (analysis.get("hechos_faltantes") or abstention) else 0.5
    scores["abstention"] = 1.0 if abstention and response.get("abstention_reason") else (0.0 if abstention else 0.5)
    scores["human_escalation"] = 1.0 if response.get("needs_hitl") else 0.5

    evidence["abstention"] = abstention
    evidence["citation_audit_executed"] = bool(audit.get("executed"))
    evidence["fidelity"] = fidelity
    evidence["blocks"] = len(blocks)

    verdict = "FAIL" if hallucinated else ("READY" if _mean(scores) >= 0.75 else ("CONDITIONAL" if _mean(scores) >= 0.5 else "FAIL"))
    return RubricResult(
        scores=scores,
        evidence=evidence,
        hallucinated_authority=hallucinated,
        verdict=verdict,
    )


def _score_list(items: Any, *, allow_empty_good: bool = True) -> float:
    if items:
        return 1.0
    return 1.0 if allow_empty_good else 0.5


def _mean(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)
