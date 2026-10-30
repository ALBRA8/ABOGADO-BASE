"""Siembra del corpus jurídico canónico en el retrieval provider.

Cierra la ruta real del conocimiento (migración DESPACHO-JURIDICO → ABOGADO-BASE):

    CORPUS EN DISCO (albra/knowledge/colombia/corpus_pilot)
        ↓  build_seeded_retriever() / seed_retrieval_provider()
    INGESTIÓN (LegalIngestionPipeline — las abstracciones existentes)
        ↓
    RETRIEVAL (InMemoryRetrievalProvider u otro RetrievalProvider)
        ↓
    LEGAL KNOWLEDGE ENGINE (órgano del runtime)
        ↓
    ABOGADO (respuestas con citas y provenance)

Reglas de esta siembra (migración de conocimiento, no refactorización):

* Fuente canónica única: corpus V1.4 (10 documentos: Constitución 1991
  completa con 380 artículos, Ley 1564/2012, Ley 640/2001, Ley 906/2004,
  Código Sustantivo del Trabajo y 5 sentencias de la Corte Constitucional,
  con raw_bytes preservados y hashes verificables) + Ley 100/1993 y
  Ley 80/1993 en su versión V1.3 (mejor provenance que V1.1).
* NO se siembran versiones subsumidas: ``const_1991_real_v11`` /
  ``const_1991_real_v13`` quedan fuera porque ``constitucion_v14``
  contiene la misma norma completa. Evita duplicar la misma norma en
  el índice (regla anti-duplicación de la migración).
* Integridad verificada: cada documento se siembra SOLO si
  ``sha256(reconstructed_text) == reconstructed_text_hash``. Si un hash
  no coincide, el documento se omite y se reporta (nunca se siembra
  contenido no verificado).
* Mapeo de tipos: el corpus usa ``codigo_sustantivo`` y
  ``jurisprudencia`` (valores que consumen norm_reference.py,
  citation_audit.py y los tests del corpus). El pipeline de ingesta
  exige tipos del esquema DOCUMENT_TYPES. El mapeo se aplica SOLO en
  la llamada de ingesta y el tipo original se conserva en la
  provenance (``corpus_document_type``). No se altera el corpus.
* Sin dependencia del despacho: todo vive en ABOGADO-BASE.
* Política de fallo en DOS niveles (no hay fail-closed global de boot):
    - Nivel 1 — integridad (fail-closed por documento): un hash
      inválido impide sembrar ESE documento y queda reportado.
    - Nivel 2 — disponibilidad (fail-open de boot): si la siembra
      completa falla, el agente arranca igual con un provider vacío y
      el organ ``legal_corpus_report`` marcado ``seed_failed=True``.
      Lo que evita afirmaciones sin conocimiento es el fail-closed de
      NIVEL RESPUESTA: abstención sin evidencia (LegalKnowledgeEngine)
      + citation audit pre-reveal (citation_audit.py).
"""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from albra.knowledge.colombia.corpus_pilot.real_corpus_v13 import (
    ALL_DOCUMENTS_V13,
)
from albra.knowledge.colombia.corpus_pilot.real_corpus_v14 import (
    ALL_DOCUMENTS_V14,
)
from albra.knowledge.colombia.corpus_pilot.real_corpus_v15 import (
    ALL_DOCUMENTS_V15,
)
from albra.knowledge.ingestion import LegalIngestionPipeline
from albra.knowledge.retrieval import HybridRetriever
from albra.knowledge.retrieval_providers import InMemoryRetrievalProvider
from albra.knowledge.schemas import SourceTier
from albra.observability.logger import get_logger

log = get_logger("albra.knowledge.corpus_seed")

# Versiones del corpus subsumidas por una versión superior de la misma
# norma. NO se siembran (regla anti-duplicación). V1.4 contiene la
# Constitución completa (380 arts.); V1.5 contiene el TEXTO COMPLETO de
# Ley 100/1993 (296 arts.) y Ley 80/1993 (83 arts.), que subsume los
# fragmentos V1.3 de esas mismas leyes.
_SUBSUMED_SOURCE_IDS = {
    "const_1991_real_v11",
    "const_1991_real_v13",
    "ley_100_1993_real_v13",
    "ley_80_1993_real_v13",
}

# V1.3 ya no aporta documentos vivos al canónico: sus leyes viven
# completas en V1.5 y su Constitución en V1.4. Se conserva el import
# para compatibilidad y para los tests de V1.3.
_V13_SOURCE_IDS_TO_SEED: set[str] = set()

# Mapeo corpus → esquema DOCUMENT_TYPES (sólo en la llamada de ingesta;
# el tipo original del corpus se conserva en provenance).
_INGESTION_TYPE_MAP = {
    "codigo_sustantivo": "codigo",
    "jurisprudencia": "sentencia",
}

# V1.5 (11 documentos: 6 normas completas + 5 sentencias) + V1.4 (5 normas
# + 5 sentencias) = 21 documentos.
CORPUS_VERSION = "V1.5+V1.4"


@dataclass
class CorpusSeedReport:
    """Resultado verificable de la siembra del corpus.

    ``seed_failed`` es SIEMPRE explícito (contrato de observabilidad):
    ``False`` en la ruta exitosa, ``True`` en el fallback degradado que
    construye ``Agent.boot()``. Un consumidor nunca debe adivinar el
    estado por ausencia de la clave.
    """

    corpus_version: str = CORPUS_VERSION
    seed_failed: bool = False
    ingested: int = 0
    skipped_hash_mismatch: list[str] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "corpus_version": self.corpus_version,
            "seed_failed": self.seed_failed,
            "ingested": self.ingested,
            "skipped_hash_mismatch": self.skipped_hash_mismatch,
            "rejected": self.rejected,
            "documents": self.documents,
            "stats": self.stats,
        }


def canonical_corpus_documents() -> list[tuple[str, dict[str, Any]]]:
    """Corpus canónico a sembrar: V1.5 completo + V1.4 completo.

    Devuelve pares (categoría, documento) sin versiones subsumidas.
    Las leyes V1.3 de Ley 100/Ley 80 quedaron subsumidas por sus textos
    completos en V1.5 (regla anti-duplicación).
    """
    out: list[tuple[str, dict[str, Any]]] = []
    for category, doc in ALL_DOCUMENTS_V15:
        out.append((category, doc))
    for category, doc in ALL_DOCUMENTS_V14:
        out.append((category, doc))
    for category, doc in ALL_DOCUMENTS_V13:
        if doc["source_id"] in _V13_SOURCE_IDS_TO_SEED:
            out.append((category, doc))
    return out


def verify_corpus_hashes() -> list[str]:
    """Verifica sha256(reconstructed_text) == reconstructed_text_hash.

    Devuelve la lista de source_ids cuyo hash NO coincide (vacía = OK).
    """
    mismatched: list[str] = []
    for _, doc in canonical_corpus_documents():
        text = doc.get("reconstructed_text", "")
        expected = doc.get("reconstructed_text_hash", "")
        if not expected or hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            mismatched.append(doc["source_id"])
    return mismatched


def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _caller_provenance(doc: dict[str, Any]) -> dict[str, Any]:
    """Provenance del corpus que viaja con el documento indexado.

    El pipeline (B4) sobrescribe los campos calculados por el sistema;
    aquí sólo aportamos los metadatos originales del corpus.
    """
    prov: dict[str, Any] = {}
    corpus_prov = doc.get("provenance")
    if corpus_prov is not None:
        try:
            from dataclasses import asdict, is_dataclass

            if is_dataclass(corpus_prov):
                prov["corpus_provenance"] = asdict(corpus_prov)
            else:
                prov["corpus_provenance"] = corpus_prov
        except Exception:  # noqa: BLE001 — provenance es metadata, nunca bloquea
            prov["corpus_provenance"] = str(corpus_prov)
    prov["corpus_document_type"] = doc.get("document_type", "")
    prov["corpus_provenance_status"] = doc.get("provenance_status", "")
    prov["corpus_version"] = CORPUS_VERSION
    return prov


async def seed_retrieval_provider(
    provider: Any,
    *,
    retriever: HybridRetriever | None = None,
) -> CorpusSeedReport:
    """Siembra el corpus canónico en el provider dado (ruta real).

    Usa las abstracciones existentes (LegalIngestionPipeline). Verifica
    hashes ANTES de ingestar: un documento con hash inválido se omite y
    queda reportado; nunca se siembra contenido no verificado.
    """
    report = CorpusSeedReport()
    ret = retriever or HybridRetriever(provider=provider)
    pipeline = LegalIngestionPipeline(retriever=ret)

    await provider.startup()

    for category, doc in canonical_corpus_documents():
        source_id = doc["source_id"]
        text = doc.get("reconstructed_text", "")
        raw = text.encode("utf-8")

        # 1. Integridad ANTES de ingestar (fail-closed por documento).
        expected = doc.get("reconstructed_text_hash", "")
        computed = hashlib.sha256(raw).hexdigest()
        if not expected or computed != expected:
            report.skipped_hash_mismatch.append(source_id)
            log.warning(
                "corpus_seed.hash_mismatch", source_id=source_id,
                expected=str(expected)[:12], computed=computed[:12],
            )
            continue

        document_type = _INGESTION_TYPE_MAP.get(
            doc["document_type"], doc["document_type"]
        )

        result = await pipeline.ingest(
            source_id=source_id,
            raw_content=raw,
            source_url=doc["source_url"],
            authority=doc["authority"],
            document_type=document_type,
            title=doc.get("title", ""),
            number=doc.get("number", ""),
            date_issued=_parse_date(doc.get("date_issued")),
            publication_date=_parse_date(doc.get("publication_date")),
            effective_from=_parse_date(doc.get("effective_from")),
            effective_until=_parse_date(doc.get("effective_until")),
            status=doc.get("status", "vigente"),
            source_tier=SourceTier[doc["source_tier"]],
            jurisdiction=doc.get("jurisdiction", "CO"),
            articles=doc.get("articles"),
            provenance=_caller_provenance(doc),
            reach=doc.get("reach"),
            force=doc.get("force"),
        )

        if result.ok:
            report.ingested += 1
            report.documents.append({
                "source_id": source_id,
                "category": category,
                "document_type": document_type,
                "corpus_document_type": doc.get("document_type", ""),
                "articles": len(doc.get("articles", [])),
                "content_hash": result.content_hash,
                "reconstructed_text_hash": doc.get("reconstructed_text_hash", ""),
                "hash_verified": True,
                "jurisdiction": doc.get("jurisdiction", "CO"),
                "source_tier": doc["source_tier"],
                "authority": doc["authority"],
                "provenance_status": doc.get("provenance_status", ""),
            })
        else:
            report.rejected.append({
                "source_id": source_id,
                "error": result.error,
            })
            log.warning("corpus_seed.rejected", source_id=source_id, error=result.error)

    report.stats = provider.stats()

    # Enriquecimiento de jurisprudencia con metadatos REALES (Fase
    # Producción Real): ponente, fecha de resolución y tema extraídos
    # del TEXTO COMPLETO de la fuente (los metadatos están en el
    # encabezado de la sentencia, fuera del primer fragmento indexado).
    # Nada se inventa: lo que la sentencia no declara queda como estaba.
    try:
        from albra.knowledge.jurisprudence_metadata import (
            extract_sentencia_metadata,
        )

        full_text_by_number = {
            doc.get("number", ""): doc.get("reconstructed_text", "")
            for _, doc in canonical_corpus_documents()
            if doc.get("document_type") == "jurisprudencia"
        }
        for j in provider.jurisprudence_items():
            if getattr(j, "_metadata_enriched", False):
                continue
            text = full_text_by_number.get(j.file_number, "") or j.decision or ""
            meta = extract_sentencia_metadata(text)
            if meta.get("ponentes") and not j.ponente:
                j.ponente = meta["ponentes"][0]
            if meta.get("fecha_resolucion"):
                try:
                    from datetime import date as _d

                    j.decision_date = _d.fromisoformat(meta["fecha_resolucion"])
                except ValueError:
                    pass
            j._metadata_enriched = True
    except Exception as e:  # noqa: BLE001 — el enriquecimiento nunca bloquea la siembra
        log.warning("corpus_seed.jurisprudence_enrichment_failed", error=str(e))

    log.info(
        "corpus_seed.complete",
        ingested=report.ingested,
        skipped=len(report.skipped_hash_mismatch),
        rejected=len(report.rejected),
        stats=report.stats,
    )
    return report


async def build_seeded_retriever() -> tuple[HybridRetriever, CorpusSeedReport]:
    """Retriever híbrido con el corpus jurídico canónico ya sembrado.

    Es la pieza que el boot del agente usa para que el
    LegalKnowledgeEngine arranque CON conocimiento (no con un provider
    vacío).

    Esta función NO traga errores: si la siembra falla, propaga la
    excepción. Es el boot del agente (identity/agent.py) quien decide
    el fallback fail-open de disponibilidad (provider vacío + reporte
    marcado ``seed_failed=True``); ver la política de dos niveles en el
    docstring del módulo.
    """
    provider = InMemoryRetrievalProvider()
    retriever = HybridRetriever(provider=provider)
    report = await seed_retrieval_provider(provider, retriever=retriever)
    return retriever, report


# ---------------------------------------------------------------------
# Helpers síncronos (CLI / pruebas rápidas)
# ---------------------------------------------------------------------

def seed_sync() -> CorpusSeedReport:
    """Siembra en un provider desechable y devuelve el reporte."""
    async def _run() -> CorpusSeedReport:
        provider = InMemoryRetrievalProvider()
        try:
            return await seed_retrieval_provider(provider)
        finally:
            await provider.shutdown()

    return asyncio.run(_run())


def new_corpus_document_id() -> str:
    """Expone el esquema de IDs del pipeline (uso interno/tests)."""
    return uuid.uuid4().hex[:16]
