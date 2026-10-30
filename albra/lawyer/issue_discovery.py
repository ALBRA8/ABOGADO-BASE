"""DESCUBRIMIENTO DE PROBLEMAS JURÍDICOS Y PROPUESTA DE FUENTES — P1.

Cierre de extracción (hallazgo 5 — autonomía de LawyerExam): hasta ahora
el examen recibía ``legal_issues`` y ``required_sources`` desde el caso,
y abstenía el paso 3 si el caso no los declaraba. La capacidad del
abogado de DELIMITAR problemas y PROPONER fuentes a partir de los hechos
era la pieza incompleta.

Este módulo COMPLETA esa capacidad con reglas deterministas sobre los
componentes existentes (``LegalQueryClassifier``, ``KnowledgeTriage`` y
el catálogo de documentos del corpus canónico). NO es un motor nuevo y
NO introduce conocimiento externo:

* Los dominios se derivan de los documentos que el corpus canónico
  realmente contiene (Constitución, CGP, Ley 640, CPP, CST, Ley 100,
  Ley 80) — el texto de cada ley declara su materia en su título.
* Las propuestas se derivan de los hechos/documentos recibidos: nunca
  se inventan artículos, sentencias ni datos del caso.
* Toda fuente propuesta sale marcada ``proposed_by_agent=True`` y DEBE
  pasar por la verificación de corpus del examen (pasos 5-6). Lo que no
  se encuentre queda expresamente SIN VERIFICAR.
"""
from __future__ import annotations

import re
from typing import Any

from albra.knowledge.query_classifier import LegalQueryClassifier

# ---------------------------------------------------------------------
# Dominios → documentos del corpus canónico. El mapeo se deriva del
# TÍTULO declarado de cada documento del corpus (dato existente, no
# conocimiento inventado):
#   Constitución Política de Colombia → constitucional
#   Ley 1564/2012 — Código General del Proceso → procesal civil
#   Ley 640/2001 — Conciliación → conciliación
#   Ley 906/2004 — Código de Procedimiento Penal → penal
#   Código Sustantivo del Trabajo (Decreto 2663/1950) → laboral
#   Ley 100/1993 — sistema de seguridad social → seguridad social
#   Ley 80/1993 — Estatuto General de Contratación → contratación pública
# ---------------------------------------------------------------------

DOMAINS: dict[str, dict[str, Any]] = {
    "laboral": {
        "corpus_slug": "codigo_sustantivo_trabajo",
        "document_alias": "codigo sustantivo del trabajo",
        "keywords": (
            "trabajador", "empleador", "despido", "jornada", "salario",
            "sindicato", "prestaciones", "cesantía", "cesantias",
            "liquidación", "liquidacion", "contrato de trabajo",
            "vacaciones", "accidente de trabajo", "convenio",
            "remuneración", "remuneracion", "minimetro", "descanso",
        ),
        "issue": (
            "Determinar el régimen laboral aplicable a la relación entre "
            "las partes conforme al Código Sustantivo del Trabajo."
        ),
    },
    "procesal_civil": {
        "corpus_slug": "ley_1564_2012",
        "document_alias": "ley 1564 de 2012",
        "keywords": (
            "demanda", "contestación", "contestacion", "prueba", "pruebas",
            "competencia", "apelación", "apelacion", "casación",
            "casacion", "notificación", "notificacion", "término procesal",
            "termino procesal", "audiencia", "sentencia de primera instancia",
            "proceso", "procesal",
        ),
        "issue": (
            "Determinar trámite, competencia y términos procesales "
            "aplicables conforme al Código General del Proceso (Ley 1564 de 2012)."
        ),
    },
    "conciliacion": {
        "corpus_slug": "ley_0640_2001",
        "document_alias": "ley 640 de 2001",
        "keywords": (
            "conciliación", "conciliacion", "centro de conciliación",
            "centro de conciliacion", "acuerdo conciliatorio", "audiencia de conciliación",
        ),
        "issue": (
            "Determinar requisitos y efectos de la conciliación conforme "
            "a la Ley 640 de 2001."
        ),
    },
    "penal": {
        "corpus_slug": "ley_0906_2004",
        "document_alias": "ley 906 de 2004",
        "keywords": (
            "fiscalía", "fiscalia", "imputación", "imputacion", "delito",
            "medida cautelar", "indagatoria", "prisión", "prision",
            "investigación penal", "investigacion penal", "acusación",
            "acusacion", "penal", "vinculado", "víctima", "victima",
        ),
        "issue": (
            "Determinar etapas, términos y garantías del proceso penal "
            "aplicables conforme a la Ley 906 de 2004."
        ),
    },
    "seguridad_social": {
        "corpus_slug": "ley_100_1993",
        "document_alias": "ley 100 de 1993",
        "keywords": (
            "salud", "eps", "pensión", "pension", "seguridad social",
            "afiliación", "afiliacion", "cotización", "cotizacion",
            "incapacidad", "riesgos laborales", "arp", "salario mínimo",
            "salario minimo",
        ),
        "issue": (
            "Determinar la cobertura y requisitos del sistema de "
            "seguridad social conforme a la Ley 100 de 1993."
        ),
    },
    "contratacion_publica": {
        "corpus_slug": "ley_80_1993",
        "document_alias": "ley 80 de 1993",
        "keywords": (
            "entidad estatal", "licitación", "licitacion", "contrato estatal",
            "concesión", "concesion", "contratación pública",
            "contratacion publica", "garantías contractuales",
            "garantias contractuales", "selección del contratista",
        ),
        "issue": (
            "Determinar el régimen de contratación estatal aplicable "
            "conforme al Estatuto General de Contratación (Ley 80 de 1993)."
        ),
    },
    "constitucional": {
        "corpus_slug": "constitucion",
        "document_alias": "constitucion",
        "keywords": (
            "tutela", "derecho fundamental", "derechos fundamentales",
            "debido proceso", "igualdad", "constitución", "constitucion",
            "acción de tutela", "accion de tutela", "habeas data",
            "libertad", "dignidad humana",
        ),
        "issue": (
            "Determinar el alcance del derecho constitucional invocado "
            "y su garantía conforme a la Constitución Política de 1991."
        ),
    },
}

_ARTICLE_RE = re.compile(
    r"art[ií]culo\s+(\d{1,3}(?:\s*(?:bis|ter|quater))?)",
    re.IGNORECASE,
)

# Alias aceptados por LawyerExam._lookup_in_corpus para los docs del corpus.
_LOOKUP_ALIASES = {
    "constitucion": "constitucion",
    "codigo_sustantivo_trabajo": "codigo_sustantivo_trabajo",
    "ley_1564_2012": "ley_1564_2012",
    "ley_0640_2001": "ley_0640_2001",
    "ley_0906_2004": "ley_0906_2004",
    "ley_100_1993": "ley_100",
    "ley_80_1993": "ley_80",
}


def _case_text(case_facts: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("summary", "facts", "documents", "uncertainties"):
        v = case_facts.get(key, [])
        if isinstance(v, str):
            parts.append(v)
        else:
            parts.extend(str(x) for x in v)
    return " \n".join(parts)


def discover_domains(case_facts: dict[str, Any]) -> dict[str, list[str]]:
    """Detecta dominios jurídicos en los hechos con sus evidencias.

    Returns:
        {dominio: [fragmentos de los hechos que dispararon el match]}
    """
    text = _case_text(case_facts)
    text_lower = text.lower()
    found: dict[str, list[str]] = {}
    for domain, cfg in DOMAINS.items():
        hits: list[str] = []
        for kw in cfg["keywords"]:
            if kw in text_lower:
                # Evidencia: el fragmento declarado que contiene la keyword
                for frag in text_lower.split("\n"):
                    if kw in frag:
                        hits.append(frag.strip()[:120])
        if hits:
            found[domain] = hits[:3]
    return found


def discover_legal_issues(case_facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Propone problemas jurídicos A PARTIR de los hechos recibidos.

    Determinista: dominio detectado → objetivo de investigación (el
    issue del dominio). No afirma conclusiones ni inventa hechos.
    """
    domains = discover_domains(case_facts)
    issues: list[dict[str, Any]] = []
    for domain in domains:
        cfg = DOMAINS[domain]
        issues.append({
            "issue": cfg["issue"],
            "domain": domain,
            "corpus_slug": cfg["corpus_slug"],
            "proposed_by_agent": True,
            "basis": [
                f"hecho declarado: «{h}»" for h in domains[domain][:2]
            ],
        })
    return issues


def propose_required_sources(
    case_facts: dict[str, Any],
    discovered_issues: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Propone fuentes a investigar: normas del corpus por dominio +
    artículo específico cuando el texto de los hechos cita uno.

    Toda fuente sale con ``proposed_by_agent=True`` y ``verified=False``
    (sin verificar hasta que el paso 5 la contraste contra el corpus).
    """
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add(doc: str, article: str, basis: str) -> None:
        key = (doc.lower(), article)
        if key in seen:
            return
        seen.add(key)
        sources.append({
            "document": doc,
            "article": article,
            "proposed_by_agent": True,
            "verified": False,
            "basis": basis,
        })

    issues = discovered_issues if discovered_issues is not None else discover_legal_issues(case_facts)
    for issue in issues:
        alias = _LOOKUP_ALIASES.get(issue.get("corpus_slug", ""))
        if alias:
            _add(alias, "", f"dominio detectado: {issue.get('domain')}")

    # Artículos específicos citados en los hechos/documentos.
    classifier = LegalQueryClassifier()
    text = _case_text(case_facts)
    for sentence in re.split(r"[.\n;]", text):
        if "artícul" not in sentence.lower() and "articulo" not in sentence.lower():
            continue
        m = _ARTICLE_RE.search(sentence)
        if not m:
            continue
        cls = classifier.classify(sentence.strip())
        if not cls.detected_norm:
            continue
        detected_norm = cls.detected_norm.strip().lower()
        # Mapear la norma detectada a un documento del corpus.
        norm_alias = ""
        for alias_key, alias_val in _LOOKUP_ALIASES.items():
            core = alias_key.split("_")[0]
            if core and core in detected_norm:
                norm_alias = alias_val
                break
        # "código sustantivo" / "cst" → laboral; "constitución" → constitucion
        if not norm_alias:
            if "sustantivo" in detected_norm or "trabajo" in detected_norm:
                norm_alias = "codigo sustantivo del trabajo"
            elif "constituci" in detected_norm:
                norm_alias = "constitucion"
            elif "1564" in detected_norm or "general del proceso" in detected_norm:
                norm_alias = "ley 1564 de 2012"
            elif "640" in detected_norm:
                norm_alias = "ley 640 de 2001"
            elif "906" in detected_norm or "procedimiento penal" in detected_norm:
                norm_alias = "ley 906 de 2004"
            elif "100" in detected_norm or "seguridad social" in detected_norm:
                norm_alias = "ley 100 de 1993"
            elif "80" in detected_norm or "contrataci" in detected_norm:
                norm_alias = "ley 80 de 1993"
        if norm_alias:
            _add(norm_alias, m.group(1), f"artículo citado en los hechos: art. {m.group(1)} ({cls.detected_norm.strip()})")
    return sources
