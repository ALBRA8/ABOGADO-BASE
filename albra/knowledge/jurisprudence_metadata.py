"""CAPA DE JURISPRUDENCIA REAL — metadatos extraídos del texto de la fuente.

Las sentencias de la Corte Constitucional (10 en el corpus canónico,
todas con raw_bytes preservados de la relatoria oficial) contienen sus
metadatos EN EL PROPIO TEXTO. Esta capa los extrae de forma
determinista — sin inventar nada: lo que la página no declara queda
None.

Extrae:
  - expediente (radicado interno real, distinto del id de citación)
  - ponentes ("Magistrado Ponente: Dr. ...")
  - sala ("La Sala Segunda de Revisión...", "Sala Plena")
  - fecha de resolución ("Bogotá, DC, treinta y uno (31) de julio de
    dos mil ocho (2008)" → 2008-07-31 — los dígitos entre paréntesis
    que la relatoria imprime hacen la fecha verificable)
  - tema/referencia (encabezado temático de la relatoria)

Y clasifica el VALOR DEL PRECEDENTE (PROMPT §14):
  - VERIFICADA   — provenance oficial con hash verificado
  - VINCULANTE   — force erga_omnes+vinculante (C, SU y T de revisión)
  - PERSUASIVA   — fuerza menor declarada
La distinción CONTRADICTORIA se evalúa en tiempo de consulta con los
conflictos detectados por el verifier (no aquí).
"""
from __future__ import annotations

import re
from typing import Any

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# "Bogotá, DC, treinta y uno (31) de julio de dos mil ocho (2008)"
_RE_FECHA = re.compile(
    r'\((\d{1,2})\)\s+de\s+(' + "|".join(_MESES) + r')\s+de\s+[a-záéíóúñ\s]+?\((\d{4})\)',
    re.IGNORECASE,
)
_RE_EXPEDIENTE = re.compile(
    r'expediente\s+((?:T|C|SU|G)[-.\s]?[\d.]+)', re.IGNORECASE
)
_RE_PONENTES = re.compile(
    r'(?:Magistrado\s+)?Ponentes?\s*:?\s*(.+?)(?=Bogot|$)',
    re.IGNORECASE | re.DOTALL,
)
_RE_SALA = re.compile(
    r'La\s+(Sala\s+Plena|Sala\s+[A-Za-z]+(?:\s+de\s+Revisi[oó]n(?:\s+de\s+tutelas)?)?'
    r'|Sala\s+Disciplinaria|Sala\s+Administrativa|Sala\s+Laboral|Sala\s+Civil'
    r'|Sala\s+Penal|Sala\s+Consultativa|Sala\s+de\s+Selecci[oó]n)'
    r'(?=\s+(?:de la Corte|de la Corte Suprema|,|\.|en\b))'
)
_RE_TEMA = re.compile(
    r'Sentencia\s+[TCU]{1,2}-?[\d/]+\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s/-]{10,90})'
)


def extract_sentencia_metadata(text: str) -> dict[str, Any]:
    """Extrae metadatos reales del texto de una sentencia (determinista).

    Devuelve {expediente, ponentes, sala, fecha_resolucion, tema} con
    None donde la fuente no declara el dato.
    """
    out: dict[str, Any] = {
        "expediente": None,
        "ponentes": None,
        "sala": None,
        "fecha_resolucion": None,
        "tema": None,
    }
    if not text:
        return out

    m = _RE_EXPEDIENTE.search(text)
    if m:
        out["expediente"] = m.group(1).strip().rstrip(".")

    m = _RE_PONENTES.search(text)
    if m:
        raw = " ".join(m.group(1).split())
        # dividir múltiples ponentes por los títulos Dr./Dra.
        parts = re.split(r'(?=(?:Dr\.?|Dra\.?)\s+[A-ZÁÉÍÓÚÑ])', raw)
        ponentes = [p.strip(" .,-") for p in parts if p.strip(" .,-")]
        if ponentes:
            out["ponentes"] = ponentes

    ib = text.lower().find("bogot")
    if ib >= 0:
        region = text[ib:ib + 220]
        m = _RE_FECHA.search(region)
        if m:
            dia, mes, anio = int(m.group(1)), _MESES[m.group(2).lower()], int(m.group(3))
            try:
                import datetime as _dt

                out["fecha_resolucion"] = _dt.date(anio, mes, dia).isoformat()
            except ValueError:
                pass

    m = _RE_SALA.search(text)
    if m:
        out["sala"] = " ".join(m.group(1).split())

    m = _RE_TEMA.search(text)
    if m:
        out["tema"] = m.group(1).strip(" -")

    return out


def classify_precedent(
    *,
    verified: bool,
    force: str | None,
    in_conflict: bool = False,
) -> str:
    """Clasifica el valor del precedente para una consulta dada.

    - NO_VERIFICADA      — sin provenance verificada (no se presenta)
    - VINCULANTE         — erga omnes + vinculante (C/SU/T revisión)
    - PERSUASIVA         — fuerza menor declarada
    - CONTRADICTORIA     — coexiste con otra sentencia en conflicto
    """
    if not verified:
        return "NO_VERIFICADA"
    if in_conflict:
        return "CONTRADICTORIA"
    f = (force or "").lower()
    if "erga_omnes" in f or "vinculante" in f:
        return "VINCULANTE"
    return "PERSUASIVA"


def corpus_jurisprudence_metadata() -> list[dict[str, Any]]:
    """Metadatos de TODAS las sentencias del corpus canónico.

    Cada entrada lleva la provenance (source_url + hash del documento)
    y el estado de verificación — los metadatos se leen del texto REAL
    preservado, nunca se rellenan a mano.
    """
    from albra.knowledge.corpus_seed import canonical_corpus_documents

    out: list[dict[str, Any]] = []
    for _, doc in canonical_corpus_documents():
        if doc.get("document_type") != "jurisprudencia":
            continue
        meta = extract_sentencia_metadata(doc.get("reconstructed_text", ""))
        meta.update({
            "sentencia_id": doc.get("number", ""),
            "title": doc.get("title", ""),
            "source_url": doc.get("source_url", ""),
            "content_hash": doc.get("reconstructed_text_hash", ""),
            "force": doc.get("force", ""),
            "verification": "VERIFIED" if doc.get("provenance_status") == "VERIFIED" else "NO_VERIFICADA",
        })
        out.append(meta)
    return out
