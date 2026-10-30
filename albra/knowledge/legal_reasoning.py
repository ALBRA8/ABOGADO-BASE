"""ANÁLISIS JURÍDICO ESTRUCTURADO — cierre de extracción ABOGADO-BASE.

Completar la capacidad de análisis del ``LegalKnowledgeEngine`` usando
SOLO componentes que ya existen. NO es un motor nuevo: es el paso que
construye, de forma DETERMINISTA y sobre la evidencia YA verificada por
el pipeline del engine, la estructura de razonamiento que el examen del
abogado (LawyerExam V7.0 pasos 2-3-7-8) exige:

    Hechos → Problemas jurídicos → Normas aplicables →
    Jurisprudencia → Contrastación de evidencias →
    Argumentos → Contraargumentos y riesgos → Conclusión fundamentada

Reglas inviolables de este módulo:

* Cada afirmación construida aquí referencia las citas que la
  respaldan (``LegalArgument.citations``). Una afirmación sin citas se
  marca como hipótesis NO confirmada, nunca como conclusión.
* El razonamiento generado por un proveedor LLM nunca sustituye la
  verificación de las fuentes. Este módulo NO invoca LLM: deriva todo
  de (a) la consulta clasificada y (b) el VerificationResult del
  engine. Lo que el usuario declaró se reporta como hecho declarado;
  lo que el sistema deduce se marca como inferencia.
* La conclusión SOLO se apoya en evidencia con fuente primaria S0/S1
  y vigente, o queda explícitamente sin soporte.
* La paráfrasis no demostrada NUNCA se declara verificada: la
  fidelidad la calcula ``CitationAuditor`` (document_only /
  literal_retraced), no este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from albra.knowledge.citation import Citation
from albra.knowledge.query_classifier import QueryClassification
from albra.knowledge.verification import VerificationResult

# Tipos de documento que constituyen norma normativa aplicable.
_NORM_DOC_TYPES = ("ley", "decreto", "codigo", "estatuto", "constitucion", "norma")
_JURIS_DOC_TYPES = ("sentencia", "auto")

# Niveles de fuente que pueden sostener una conclusión jurídica.
_CONCLUSION_TIERS = ("S0_PRIMARY_SUPERIOR", "S1_OFFICIAL")


@dataclass
class LegalArgument:
    """Una afirmación del análisis con sus citas de respaldo."""

    claim: str
    kind: str = "inferencia"  # hecho_declarado | inferencia | hipotesis
    basis: str = ""           # "norma" | "jurisprudencia" | "norma+jurisprudencia"
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "kind": self.kind,
            "basis": self.basis,
            "citations": [c.as_dict() for c in self.citations],
            "confidence": self.confidence,
        }


@dataclass
class LegalAnalysis:
    """Análisis jurídico estructurado, trazable a evidencia verificada."""

    # Separación explícita hechos / inferencias / conclusiones
    hechos_declarados: list[str] = field(default_factory=list)
    inferencias: list[str] = field(default_factory=list)
    problemas_juridicos: list[str] = field(default_factory=list)
    hechos_faltantes: list[str] = field(default_factory=list)
    normas_aplicables: list[dict[str, Any]] = field(default_factory=list)
    jurisprudencia_pertinente: list[dict[str, Any]] = field(default_factory=list)
    contrastacion: dict[str, Any] = field(default_factory=dict)
    argumentos: list[LegalArgument] = field(default_factory=list)
    contraargumentos: list[str] = field(default_factory=list)
    riesgos: list[str] = field(default_factory=list)
    conclusion: str = ""
    conclusion_con_soporte: bool = False
    # Garantía de trazabilidad: todo argumento de tipo inferencia lleva cita
    citas_completas: bool = False
    llm_usado: bool = False  # False: análisis determinista, sin LLM

    def as_dict(self) -> dict[str, Any]:
        return {
            "hechos_declarados": self.hechos_declarados,
            "inferencias": self.inferencias,
            "problemas_juridicos": self.problemas_juridicos,
            "hechos_faltantes": self.hechos_faltantes,
            "normas_aplicables": self.normas_aplicables,
            "jurisprudencia_pertinente": self.jurisprudencia_pertinente,
            "contrastacion": self.contrastacion,
            "argumentos": [a.as_dict() for a in self.argumentos],
            "contraargumentos": self.contraargumentos,
            "riesgos": self.riesgos,
            "conclusion": self.conclusion,
            "conclusion_con_soporte": self.conclusion_con_soporte,
            "citas_completas": self.citas_completas,
            "llm_usado": self.llm_usado,
        }


def build_legal_analysis(
    *,
    query_text: str,
    classification: QueryClassification,
    verification: VerificationResult,
    citations: list[Citation],
) -> LegalAnalysis:
    """Construye el análisis jurídico a partir de evidencia YA verificada.

    NO re-recupera, NO re-verifica, NO consulta LLM: consume el mismo
    ``VerificationResult`` del pipeline del engine (fuente única), por
    lo que no puede introducir evidencia que el engine no haya visto.
    """
    analysis = LegalAnalysis()

    # 1. HECHOS DECLARADOS — solo lo que la consulta aporta (no se inventa).
    analysis.hechos_declarados.append(query_text.strip())
    if classification.detected_norm:
        analysis.inferencias.append(
            f"La consulta menciona una norma identificada: {classification.detected_norm}."
        )
    if classification.detected_article:
        analysis.inferencias.append(
            f"La consulta menciona una disposición específica: {classification.detected_article}."
        )
    if classification.detected_jurisdiction:
        analysis.inferencias.append(
            f"Jurisdicción detectada: {classification.detected_jurisdiction}."
        )
    if classification.temporal_hint:
        analysis.inferencias.append(
            f"Dimensión temporal declarada: {classification.temporal_hint}."
        )

    # 2. HECHOS FALTANTES — lo que el caso no declara (detectado, no inventado).
    if not classification.temporal_hint:
        analysis.hechos_faltantes.append(
            "Fecha de los hechos no especificada: no es posible fijar la "
            "vigencia aplicable al caso concreto."
        )
    analysis.hechos_faltantes.append(
        "Partes, calidades y documentos del caso no declarados en la "
        "consulta: el análisis se limita al contenido normativo consultado."
    )

    # 3. PROBLEMAS JURÍDICOS — derivados de la clasificación existente.
    if classification.detected_norm and classification.detected_article:
        analysis.problemas_juridicos.append(
            f"Determinar el contenido y alcance de {classification.detected_article} "
            f"de {classification.detected_norm}."
        )
    elif classification.detected_norm:
        analysis.problemas_juridicos.append(
            f"Determinar el régimen aplicable según {classification.detected_norm}."
        )
    qtype_text = {
        "consulta_jurisprudencial": "Identificar la jurisprudencia aplicable a la situación planteada.",
        "consulta_vigencia": "Verificar el estado de vigencia de la norma consultada.",
        "consulta_comparativa": "Comparar los regímenes normativos implicados.",
        "consulta_procesal": "Determinar requisitos y términos procesales aplicables.",
        "consulta_interpretativa": "Interpretar el sentido de la norma consultada con soporte en fuentes.",
        "consulta_caso": "Subsumir los hechos presentados en las normas aplicables.",
        "consulta_historica": "Determinar la versión histórica aplicable de la norma.",
        "consulta_doctrinal": "Identificar la doctrina relevante y su jerarquía probatoria.",
    }.get(classification.query_type)
    if qtype_text:
        analysis.problemas_juridicos.append(qtype_text)
    if not analysis.problemas_juridicos:
        analysis.problemas_juridicos.append(
            "Determinar las fuentes normativas aplicables a la consulta."
        )

    # 4. NORMAS APLICABLES — de la evidencia verificada (candidates).
    norm_candidates = [
        c for c in verification.candidates if c.document_type in _NORM_DOC_TYPES
    ]
    seen_docs: set[str] = set()
    for c in norm_candidates:
        if c.document_id in seen_docs:
            continue
        seen_docs.add(c.document_id)
        analysis.normas_aplicables.append({
            "document_id": c.document_id,
            "citation": c.citation,
            "authority": c.authority,
            "source_tier": c.source_tier.name,
            "is_current": c.is_current,
            "status": c.provenance.get("status", ""),
            "content_hash": c.provenance.get("content_hash", ""),
        })

    # 5. JURISPRUDENCIA PERTINENTE — de la misma evidencia verificada.
    juris_candidates = [
        c for c in verification.candidates if c.document_type in _JURIS_DOC_TYPES
    ]
    for c in juris_candidates:
        analysis.jurisprudencia_pertinente.append({
            "document_id": c.document_id,
            "citation": c.citation,
            "court": c.authority,
            "source_tier": c.source_tier.name,
            "snippet": c.snippet[:200],
            "reach": c.provenance.get("reach", ""),
            "force": c.provenance.get("force", ""),
        })

    # 6. CONTRASTACIÓN DE EVIDENCIAS — conflicto ya detectado por el verifier.
    analysis.contrastacion = {
        "candidatos_evaluados": len(verification.candidates),
        "conflictos": [
            {"kind": c.kind, "description": c.description, "severity": c.severity}
            for c in verification.conflicts
        ],
        "requiere_revision_humana": verification.needs_hitl,
        "fuente_primaria": verification.primary_evidence_id or "",
    }

    # 7. ARGUMENTOS — cada uno con cita (norma → texto; jurisprudencia → ratio).
    primary_citation = next(
        (c for c in citations if c.document_id == verification.primary_evidence_id),
        None,
    )
    if primary_citation is not None and norm_candidates:
        primary = next(
            (c for c in norm_candidates if c.document_id == primary_citation.document_id),
            norm_candidates[0],
        )
        analysis.argumentos.append(LegalArgument(
            claim=(
                f"El texto recuperado de la fuente consultada establece: "
                f"\"{primary.snippet}\""
            ),
            kind="inferencia",
            basis="norma",
            citations=[primary_citation],
            confidence=min(1.0, primary.score + 0.3),
        ))
    for c in juris_candidates[:3]:
        cit = next((x for x in citations if x.document_id == c.document_id), None)
        if cit is None:
            continue
        analysis.argumentos.append(LegalArgument(
            claim=(
                f"Linea jurisprudencial pertinente ({c.authority}): "
                f"\"{c.snippet}\""
            ),
            kind="inferencia",
            basis="jurisprudencia",
            citations=[cit],
            confidence=c.score,
        ))
    for c in norm_candidates:
        if c.document_id == (primary_citation.document_id if primary_citation else None):
            continue
        cit = next((x for x in citations if x.document_id == c.document_id), None)
        if cit is None or cit in [a.citations[0] for a in analysis.argumentos if a.citations]:
            continue
        analysis.argumentos.append(LegalArgument(
            claim=(
                f"Fuente normativa relacionada ({c.citation}): \"{c.snippet}\""
            ),
            kind="inferencia",
            basis="norma",
            citations=[cit],
            confidence=c.score,
        ))

    # 8. CONTRAARGUMENTOS Y RIESGOS — derivados de verificación y vigencia.
    for conflict in verification.conflicts:
        analysis.contraargumentos.append(
            f"Conflicto entre fuentes: {conflict.description}"
        )
    for c in verification.candidates:
        if not c.is_current:
            analysis.riesgos.append(
                f"Evidencia no vigente en el resultado: {c.citation} "
                f"(status={c.provenance.get('status', '')}). No debe invocarse "
                f"como derecho vigente sin verificar su versión actual."
            )
    tiers_no_primarios = [
        c for c in verification.candidates
        if c.source_tier.name not in _CONCLUSION_TIERS
    ]
    if tiers_no_primarios and not norm_candidates:
        analysis.riesgos.append(
            "La evidencia disponible no incluye fuente primaria (S0) ni "
            "oficial (S1): no puede sostener una conclusión definitiva."
        )
    if verification.needs_hitl:
        analysis.riesgos.append(
            "La verificación requiere revisión humana antes de cualquier uso."
        )

    # 9. CONCLUSIÓN — SOLO con soporte en fuente primaria vigente.
    has_primary = any(
        c.source_tier.name in _CONCLUSION_TIERS and c.is_current
        for c in verification.candidates
    )
    if primary_citation is not None and has_primary:
        analysis.conclusion = (
            f"La respuesta normativa aplicable es la transcrita de "
            f"{primary_citation.citation_text}, con provenance y hash "
            f"verificados ({primary_citation.content_hash[:12] or 'n/d'}). "
            f"Toda aplicación al caso concreto requiere los hechos "
            f"completos y revisión de abogado humano."
        )
        analysis.conclusion_con_soporte = True
    else:
        analysis.conclusion = (
            "No se puede emitir una conclusión jurídica definitiva: no hay "
            "fuente primaria vigente que respalde la afirmación. Abstenerse "
            "o requerir evidencia adicional."
        )
        analysis.conclusion_con_soporte = False

    # 10. GARANTÍA DE TRAZABILIDAD: todo argumento lleva ≥1 cita.
    analysis.citas_completas = all(
        len(a.citations) >= 1 for a in analysis.argumentos
    ) if analysis.argumentos else False
    return analysis


def analysis_to_blocks_payload(analysis: LegalAnalysis) -> dict[str, Any]:
    """Serializa el análisis para incluirlo en un LegalResponseBlock."""
    return analysis.as_dict()
