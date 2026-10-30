"""PLAN DE COBERTURA JURÍDICA — dominio, subdominio, fuente, norma, estado.

Define la matriz de cobertura objetivo para producción jurídica real
(PROMPT MAESTRO §5), con el estado HONESTO de cada cuerpo:
  - PRESENT_FULL      : texto completo ingerido del corpus canónico.
  - PRESENT_PARTIAL   : solo fragmentos (no cubre el dominio).
  - ABSENT_BLOCKED    : ausente; ingesta bloqueada por red/credenciales
                        (reintentable cuando el bloqueo cese).
  - ABSENT_DECISION   : ausente; requiere decisión de alcance
                        (¿forma parte del servicio?).
  - ABSENT_PLANNED    : ausente; sin bloqueo, pendiente de ingesta.

Cada entrada declara la fuente oficial correspondiente. NADA se marca
PRESENT sin corpus ingerido y verificado (regla del PROMPT: no asumir
que 2.200 artículos equivalen a cobertura general).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CoverageEntry:
    dominio: str
    subdominio: str
    fuente: str                      # fuente oficial correspondiente
    norma: str
    estado: str                      # PRESENT_FULL | PRESENT_PARTIAL | ...
    en_corpus: str                   # source_id canónico o "" si ausente
    articulos: int = 0
    nota: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "dominio": self.dominio,
            "subdominio": self.subdominio,
            "fuente": self.fuente,
            "norma": self.norma,
            "estado": self.estado,
            "en_corpus": self.en_corpus,
            "articulos": self.articulos,
            "nota": self.nota,
        }


# ===== Matriz de cobertura (evidencia: corpus_seed.canonical_corpus_documents) =====

COVERAGE_PLAN: list[CoverageEntry] = [
    # --- Constitucional ---
    CoverageEntry("constitucional", "constitución", "Secretaría del Senado",
                  "Constitución Política 1991", "PRESENT_FULL", "constitucion_v14", 380),
    # --- Civil ---
    CoverageEntry("civil", "código civil", "Secretaría del Senado",
                  "Ley 57 de 1887 (Código Civil)", "PRESENT_FULL", "codigo_civil_v15", 2673),
    # --- Procesal civil ---
    CoverageEntry("procesal", "proceso civil", "Secretaría del Senado",
                  "Ley 1564 de 2012 (CGP)", "PRESENT_FULL", "ley_1564_2012_v14", 627),
    CoverageEntry("procesal", "conciliación", "Secretaría del Senado",
                  "Ley 640 de 2001", "PRESENT_FULL", "ley_0640_2001_v14", 50,
                  "50 artículos (la cifra previa 51 incluía 1 artículo fantasma corregido en la Fase Producción Real)"),
    # --- Penal sustantivo ---
    CoverageEntry("penal", "código penal", "Secretaría del Senado",
                  "Ley 599 de 2000", "PRESENT_FULL", "codigo_penal_v15", 598,
                  "texto consolidado con marcadores de modificación (Ley 890/2004 et al.)"),
    # --- Procesal penal ---
    CoverageEntry("procesal", "proceso penal", "Secretaría del Senado",
                  "Ley 906 de 2004 (CPP)", "PRESENT_FULL", "ley_0906_2004_v14", 564),
    # --- Laboral ---
    CoverageEntry("laboral", "código sustantivo", "Secretaría del Senado",
                  "Decreto 2663 de 1950 (CST)", "PRESENT_FULL", "codigo_sustantivo_trabajo_v14", 485),
    # --- Seguridad social ---
    CoverageEntry("seguridad_social", "sistema integral", "Secretaría del Senado",
                  "Ley 100 de 1993", "PRESENT_FULL", "ley_100_1993_v15", 296,
                  "texto consolidado (arts. permanentes 1-289; transitorios no incluidos en la fuente base)"),
    # --- Administrativo / contencioso ---
    CoverageEntry("administrativo", "CPACA", "Secretaría del Senado",
                  "Ley 1437 de 2011", "PRESENT_FULL", "cpaca_ley_1437_2011_v15", 321),
    # --- Comercial ---
    CoverageEntry("comercial", "código de comercio", "Secretaría del Senado",
                  "Decreto 410 de 1971", "PRESENT_FULL", "codigo_comercio_v15", 2037),
    # --- Contratación estatal ---
    CoverageEntry("contratacion", "contratación estatal", "Secretaría del Senado",
                  "Ley 80 de 1993", "PRESENT_FULL", "ley_80_1993_v15", 83,
                  "texto consolidado; modificaciones relevantes (Ley 1150/2007, Ley 2170/2022) no incluidas como textos separados"),
    # --- Familia (parcial vía Código Civil; leyes especiales ausentes) ---
    CoverageEntry("familia", "código de la infancia", "Secretaría del Senado",
                  "Ley 1098 de 2006", "ABSENT_BLOCKED", "", 0,
                  "ingesta bloqueada: la fuente base con formato extraíble (Secretaría del Senado) no respondió en los intentos de esta fase; reintento planificado"),
    CoverageEntry("familia", "uniones marital de hecho", "Secretaría del Senado",
                  "Ley 54 de 1990", "ABSENT_PLANNED", "", 0),
    # --- Procesal laboral ---
    CoverageEntry("procesal", "proceso laboral", "Secretaría del Senado",
                  "Ley 2213 de 2022 (Código Procesal del Trabajo)", "ABSENT_PLANNED", "", 0),
    # --- Administrativo especial ---
    CoverageEntry("administrativo", "régimen disciplinario", "Secretaría del Senado",
                  "Ley 1952 de 2019 (Código General Disciplinario)", "ABSENT_PLANNED", "", 0),
    # --- Tributario: decisión de alcance pendiente (PROMPT §5 'si forma parte del alcance') ---
    CoverageEntry("tributario", "estatuto tributario", "Secretaría del Senado",
                  "Decreto 624 de 1989", "ABSENT_DECISION", "", 0,
                  "el PROMPT deja el alcance tributario como decisión; requiere autorización de alcance"),
    # --- Jurisprudencia ---
    CoverageEntry("jurisprudencia", "Corte Constitucional — tutelas 2020", "Corte Constitucional",
                  "T-001/20, T-002/20, T-003/20, T-100/20, T-445/20", "PRESENT_FULL",
                  "sentencias_corte_const (V1.4)", 0),
    CoverageEntry("jurisprudencia", "Corte Constitucional — sentencias emblemáticas", "Corte Constitucional",
                  "T-760/08, SU-360/99, C-355/06, C-239/97, C-075/07", "PRESENT_FULL",
                  "sentencias v15", 0),
    CoverageEntry("jurisprudencia", "Corte Suprema de Justicia", "Corte Suprema (relatoría)",
                  "casaciones civiles/penales/laborales", "ABSENT_BLOCKED", "", 0,
                  "relatoría CSJ estructurada como aplicativo (js-driven); requiere Playwright"),
    # --- Decretos reglamentarios ---
    CoverageEntry("reglamentario", "decretos reglamentarios", "Función Pública (Gestor Normativo)",
                  "varios", "ABSENT_BLOCKED", "", 0,
                  "funcionpublica.gov.co inalcanzable desde el entorno de ingesta"),
]

# Cuerpos del corpus canónico NO representados aquí ( Constitución V1.4,
# CST, CGP, CPP, Ley 640) están en las entradas PRESENT_FULL correspondientes.

DOMINIOS_REQUERIDOS_PROMPT = [
    "constitucional", "civil", "comercial", "laboral", "seguridad_social",
    "penal", "procesal", "familia", "administrativo", "contratacion",
    "jurisprudencia", "reglamentario", "tributario",
]


def coverage_summary() -> dict[str, Any]:
    """Resumen verificable: cobertura por dominio y estado."""
    by_domain: dict[str, dict[str, Any]] = {}
    for e in COVERAGE_PLAN:
        d = by_domain.setdefault(e.dominio, {
            "full": 0, "partial": 0, "absent": 0, "articulos": 0, "entries": [],
        })
        d["entries"].append(e.as_dict())
        if e.estado == "PRESENT_FULL":
            d["full"] += 1
        elif e.estado == "PRESENT_PARTIAL":
            d["partial"] += 1
        else:
            d["absent"] += 1
        d["articulos"] += e.articulos
    present = sum(1 for e in COVERAGE_PLAN if e.estado.startswith("PRESENT"))
    return {
        "total_entries": len(COVERAGE_PLAN),
        "present_full": sum(1 for e in COVERAGE_PLAN if e.estado == "PRESENT_FULL"),
        "present_partial": sum(1 for e in COVERAGE_PLAN if e.estado == "PRESENT_PARTIAL"),
        "absent": present and (len(COVERAGE_PLAN) - present),
        "total_articulos_corpus": sum(e.articulos for e in COVERAGE_PLAN),
        "by_domain": by_domain,
    }
