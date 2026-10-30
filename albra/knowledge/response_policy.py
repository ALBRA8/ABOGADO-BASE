"""POLÍTICA DE RESPUESTA JURÍDICA — human-in-the-loop (Fase Producción Real).

Decide de forma DETERMINISTA cuándo el agente puede responder y cómo:

  ANSWER                — respuesta directa con evidencia verificada y
                          sin condiciones.
  ANSWER_WITH_WARNING   — responde, pero con advertencia explícita
                          (fecha aproximada, norma no vigente hoy con
                          relevancia histórica, confianza baja).
  ABSTAIN               — no responde (sin evidencia, citas no
                          verificadas, guard histórico, datos
                          insuficientes).
  HUMAN_REVIEW_REQUIRED — la cuestión exige abogado humano (conflictos
                          de fuentes, flag needs_hitl, riesgo alto).

El orden de precedencia es de MÁS a MENOS protectora:
  ABSTAIN > HUMAN_REVIEW_REQUIRED > ANSWER_WITH_WARNING > ANSWER.
Nunca se degrada una decisión protectora.
"""
from __future__ import annotations

from typing import Any

# Riesgo alto: materias donde una respuesta sin revisión humana es
# inaceptable (PROMPT §18). La lista es conservadora y explícita.
HIGH_STAKES_DOMAINS = frozenset({
    "penal", "familia", "administrativo_disciplinario",
})

_HIGH_STAKES_HINTS = (
    "penal", "delito", "condena", "pena", "custodia", "patria potestad",
    "disciplinario", "desvinculación", "tutela de menor",
)

CONFIDENCE_FLOOR = 0.55


def decide_response_policy(
    *,
    abstention: bool,
    needs_hitl: bool = False,
    needs_clarification: bool = False,
    citation_audit: dict[str, Any] | None = None,
    verification_confidence: float | None = None,
    has_conflicts: bool = False,
    temporal_approx: bool = False,
    temporal_guard_triggered: bool = False,
    primary_norm_current: bool = True,
    query_text: str = "",
    domain: str = "",
) -> dict[str, Any]:
    """Devuelve {decision, warnings[], reasons[]} — determinista y auditable."""
    warnings: list[str] = []
    reasons: list[str] = []

    # 1) ABSTAIN — las causas duras primero
    if abstention:
        reasons.append("abstención declarada por el motor (sin evidencia o guard)")
        return {"decision": "ABSTAIN", "warnings": warnings, "reasons": reasons}
    if temporal_guard_triggered:
        reasons.append("guard de versión histórica: el texto consolidado no es la versión de la fecha")
        return {"decision": "ABSTAIN", "warnings": warnings, "reasons": reasons}
    if needs_clarification:
        reasons.append("consulta ambigua o insuficiente: se solicita aclaración")
        return {"decision": "ABSTAIN", "warnings": warnings, "reasons": reasons}
    if citation_audit is not None and citation_audit and not citation_audit.get("all_verified", True):
        reasons.append("citation audit fail-closed: cita no verificada contra el corpus")
        return {"decision": "ABSTAIN", "warnings": warnings, "reasons": reasons}

    # 2) HUMAN_REVIEW_REQUIRED
    if needs_hitl:
        reasons.append("el motor marcó needs_hitl (revisión humana requerida)")
        return {"decision": "HUMAN_REVIEW_REQUIRED", "warnings": warnings, "reasons": reasons}
    if has_conflicts:
        reasons.append("conflictos de fuentes detectados por el verifier")
        return {"decision": "HUMAN_REVIEW_REQUIRED", "warnings": warnings, "reasons": reasons}
    q = (query_text or "").lower()
    d = (domain or "").lower()
    if d in HIGH_STAKES_DOMAINS or any(h in q for h in _HIGH_STAKES_HINTS):
        reasons.append("materia de alto riesgo: interpretación con consecuencias graves")
        return {"decision": "HUMAN_REVIEW_REQUIRED", "warnings": warnings, "reasons": reasons}

    # 3) ANSWER_WITH_WARNING
    if temporal_approx:
        warnings.append(
            "fecha de referencia aproximada (solo año): la versión aplicable "
            "se determinó a 31-dic; confirme la fecha exacta de los hechos"
        )
    if not primary_norm_current:
        warnings.append(
            "la evidencia primaria NO está vigente hoy (valor histórico/"
            "comparativo; no como norma actual)"
        )
    if verification_confidence is not None and verification_confidence < CONFIDENCE_FLOOR:
        warnings.append(
            f"confianza de verificación baja ({verification_confidence:.2f} < {CONFIDENCE_FLOOR})"
        )

    if warnings:
        reasons.append("respuesta con advertencias explícitas")
        return {"decision": "ANSWER_WITH_WARNING", "warnings": warnings, "reasons": reasons}

    # 4) ANSWER
    reasons.append("evidencia verificada sin condiciones degradatorias")
    return {"decision": "ANSWER", "warnings": warnings, "reasons": reasons}
