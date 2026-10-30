"""
LEGAL KNOWLEDGE ENGINE - V1.0.

Orquesta el flujo jurídico soberano:

LegalQuery
  ↓
Query Understanding (LegalQueryClassifier)
  ↓
Retrieval Strategy (HybridRetriever)
  ↓
Knowledge Sources (RetrievalProvider)
  ↓
Evidence Candidates
  ↓
Verification + Conflict Detection (LegalVerifier)
  ↓
Abstention Policy (NO INVENTAR)
  ↓
EvidenceChain (con LegalProvenance)
  ↓
Legal Response (con citas)

NO inventa conocimiento jurídico.
NO acopla a Qdrant - usa RetrievalProvider abstraction.
España NO - Colombia SÍ.
"""
from __future__ import annotations

from typing import Any

from albra.knowledge.abstention import AbstentionPolicy
from albra.knowledge.citation import Citation, LegalResponse, LegalResponseBlock
from albra.knowledge.citation_audit import CitationAuditor
from albra.knowledge.legal_provenance import build_provenance, record_evidence_with_provenance
from albra.knowledge.legal_reasoning import LegalAnalysis, build_legal_analysis
from albra.knowledge.query_classifier import LegalQueryClassifier, QueryClassification
from albra.knowledge.retrieval import HybridRetriever, RetrievalQuery
from albra.knowledge.retrieval_providers import InMemoryRetrievalProvider
from albra.knowledge.temporal import TemporalQuery
from albra.knowledge.verification import LegalVerifier, VerificationResult
from albra.observability.logger import get_logger


class LegalKnowledgeEngine:
    """Engine soberano de conocimiento jurídico colombiano.

    Pipeline:
    LegalQuery → Query Understanding → Retrieval → Verification →
    Abstention → EvidenceChain → ANÁLISIS JURÍDICO → Citation audit
    (fail-closed pre-reveal) → Legal Response

    Cierre de extracción — la respuesta NO es solo el fragmento
    recuperado: incluye un análisis jurídico estructurado
    (``legal_reasoning.build_legal_analysis``) construido
    DETERMINISTAMENTE sobre la evidencia YA verificada (hechos
    declarados vs inferencias, problemas jurídicos, normas aplicables,
    jurisprudencia, contrastación, argumentos con cita, contraargumentos
    y conclusión). NO se invoca LLM aquí: el razonamiento de un proveedor
    LLM nunca sustituye la verificación de las fuentes.

    ANTES de revelar la respuesta, TODAS las citas construidas pasan por
    ``CitationAuditor.validate_citation_direct`` contra el corpus
    canónico V1.4+V1.3. Si una sola cita no se verifica → abstención
    (fail-closed de NIVEL RESPUESTA).
    """

    def __init__(
        self,
        *,
        retriever: HybridRetriever | None = None,
        evidence_chain: Any | None = None,
    ) -> None:
        self.log = get_logger("albra.legal_engine")
        self.retriever = retriever or HybridRetriever(
            provider=InMemoryRetrievalProvider()
        )
        self.evidence_chain = evidence_chain
        self.classifier = LegalQueryClassifier()
        self.verifier = LegalVerifier()
        self.abstention_policy = AbstentionPolicy()
        # Fail-closed pre-reveal: auditoría de citas contra el corpus
        # canónico (mismo corpus que siembra corpus_seed.py).
        self.citation_auditor = CitationAuditor(corpus_version="v14")

    async def startup(self) -> None:
        await self.retriever.provider.startup()
        self.log.info("legal_engine.startup")

    async def shutdown(self) -> None:
        await self.retriever.provider.shutdown()
        self.log.info("legal_engine.shutdown")

    async def query(self, query_text: str, *, user_role: str = "anon") -> LegalResponse:
        """Ejecuta una consulta jurídica completa."""
        # 1. Query Understanding
        classification = self.classifier.classify(query_text)

        # 2. Si necesita aclaración → pedir
        if classification.needs_clarification:
            return LegalResponse(
                query=query_text,
                query_type=classification.query_type,
                abstention=True,
                abstention_reason=classification.clarification_question,
                needs_clarification=True,
                clarification_question=classification.clarification_question,
            )

        # 3. Retrieval Strategy
        retrieval_query = self._build_retrieval_query(query_text, classification)

        # 4. Retrieval
        result = await self.retriever.retrieve(retrieval_query)

        # 5. Verification + Conflict Detection
        verification = self.verifier.verify(result)

        # 6. Abstention policy
        abstention = self.abstention_policy.evaluate(
            result=result,
            verification=verification,
            query_classification=classification,
        )

        # 7. Build response
        if abstention.abstain:
            return LegalResponse(
                query=query_text,
                query_type=classification.query_type,
                abstention=True,
                abstention_reason=abstention.reason_text,
                needs_clarification=(abstention.reason_code == "ambiguous_query"),
                clarification_question=abstention.reason_text if abstention.reason_code == "ambiguous_query" else "",
                conflicts=[c.as_dict() for c in verification.conflicts if hasattr(c, "as_dict")] if verification.conflicts else [],
                needs_hitl=(abstention.fallback_action == "hitl"),
            )

        # 6.5 GUARD DE VERSIÓN HISTÓRICA (Fase Producción Real).
        # Consulta con fecha (as_of): el corpus indexa el TEXTO
        # CONSOLIDADO. Si algún artículo citado fue modificado DESPUÉS de
        # la fecha consultada, el texto consolidado NO es la versión
        # aplicable — se abstiene en lugar de responder silenciosamente
        # con texto histórico incorrecto (regla del PROMPT: nunca usar
        # una norma actual para un hecho histórico). Si los artículos
        # no tienen modificaciones posteriores, la respuesta procede con
        # nota de contexto temporal explícita.
        as_of, temporal_precision = self._parse_as_of(classification)
        if as_of is not None:
            guard_reason = self._historical_version_guard(verification, as_of)
            if guard_reason:
                self.log.warning(
                    "legal_engine.historical_version_blocked",
                    as_of=str(as_of), reason=guard_reason,
                )
                return LegalResponse(
                    query=query_text,
                    query_type=classification.query_type,
                    abstention=True,
                    abstention_reason=guard_reason,
                    needs_hitl=True,
                )

        # 8. Build citations from evidence
        citations = self._build_citations(verification)

        # 8.5 FAIL-CLOSED PRE-REVEAL: auditar TODA cita construida contra
        # el corpus canónico ANTES de revelar la respuesta. Una sola cita
        # no verificada → abstención (nunca se muestra una cita no
        # verificada como fundamento).
        audit = self._audit_citations_pre_reveal(citations, verification)
        if not audit["all_verified"]:
            self.log.warning(
                "legal_engine.citation_audit_blocked",
                unverified=audit["unverified"], reason=audit["reason"],
            )
            return LegalResponse(
                query=query_text,
                query_type=classification.query_type,
                abstention=True,
                abstention_reason=(
                    "Citas no verificadas contra el corpus canónico: "
                    + audit["reason"]
                    + " Fail-closed: la respuesta no se revela."
                ),
                needs_hitl=True,
                citation_audit=audit,
            )

        # 9. Record evidence with legal provenance
        if self.evidence_chain and verification.primary_evidence_id:
            primary_candidate = next(
                (c for c in verification.candidates if c.source_id == verification.primary_evidence_id),
                None,
            )
            if primary_candidate:
                prov = build_provenance(
                    source_url=primary_candidate.provenance.get("source_url", ""),
                    source_tier=primary_candidate.source_tier.name,
                    authority=primary_candidate.authority,
                    document_id=primary_candidate.document_id,
                    document_type=primary_candidate.document_type,
                    citation_text=primary_candidate.citation,
                    content_hash=primary_candidate.provenance.get("content_hash", ""),
                    fragment_used=primary_candidate.snippet[:200],
                    version=str(primary_candidate.provenance.get("version", "")),
                    effective_at=str(primary_candidate.provenance.get("effective_from", "")),
                )
                await record_evidence_with_provenance(
                    self.evidence_chain,
                    kind="legal_evidence",
                    content=primary_candidate.snippet,
                    source=primary_candidate.provenance.get("source_url") or primary_candidate.authority,
                    legal_provenance=prov,
                    metadata={
                        "query": query_text,
                        "query_type": classification.query_type,
                        "is_current": primary_candidate.is_current,
                        "score": primary_candidate.score,
                    },
                )

        # 10. Build response blocks (texto normativo/jurisprudencia +
        # análisis jurídico estructurado)
        blocks = self._build_response_blocks(
            query_text, classification, verification, citations
        )

        # 10.5 ANÁLISIS JURÍDICO ESTRUCTURADO (determinista, sobre la
        # misma evidencia verificada — sin LLM, sin nueva recuperación).
        analysis = build_legal_analysis(
            query_text=query_text,
            classification=classification,
            verification=verification,
            citations=citations,
        )
        blocks.append(self._analysis_block(analysis))

        # 10.6 CONTEXTO TEMPORAL EXPLÍCITO (as_of): la respuesta declara
        # la fecha de referencia, su precisión y el alcance del texto
        # consolidado — nunca un hecho histórico “en silencio”.
        if as_of is not None:
            blocks.append(LegalResponseBlock(
                content_type="interpretacion",
                text=(
                    f"CONTEXTO TEMPORAL: fecha de referencia {as_of.isoformat()} "
                    f"(precisión: {temporal_precision or 'approx'}). "
                    "Los artículos citados no registran modificaciones posteriores "
                    "a esa fecha según los marcadores del texto de la fuente. "
                    "El corpus indexa texto consolidado: para certificar la "
                    "versión histórica exacta se requiere ingesta de versiones "
                    "históricas o revisión humana."
                ),
                confidence=0.6,
                needs_review=(temporal_precision == "approx"),
            ))

        return LegalResponse(
            query=query_text,
            query_type=classification.query_type,
            blocks=blocks,
            abstention=False,
            conflicts=[
                {"kind": c.kind, "description": c.description, "severity": c.severity}
                for c in verification.conflicts
            ] if verification.conflicts else [],
            needs_hitl=verification.needs_hitl,
            citation_audit=audit,
            legal_analysis=analysis.as_dict(),
        )

    def _build_retrieval_query(
        self,
        query_text: str,
        classification: QueryClassification,
    ) -> RetrievalQuery:
        """Construye la query de retrieval según el tipo de consulta."""
        # Default: hybrid
        query_type = "hybrid"
        # Si hay artículo + norma identificados → exact match (score=1.0)
        if classification.detected_article and classification.detected_norm:
            query_type = "exact"
        elif classification.query_type == "consulta_articulo_especifico":
            query_type = "exact"
        elif classification.query_type == "consulta_jurisprudencial":
            query_type = "semantic"

        # Temporal
        temporal = None
        if classification.temporal_hint == "current":
            temporal = TemporalQuery(query_type="current")
        elif classification.temporal_hint == "historical":
            temporal = TemporalQuery(query_type="historical")
        elif classification.temporal_hint.startswith("as_of:"):
            from datetime import date
            date_str = classification.temporal_hint[6:]
            try:
                as_of = date.fromisoformat(date_str)
                temporal = TemporalQuery(query_type="as_of", as_of=as_of)
            except ValueError:
                temporal = None

        return RetrievalQuery(
            query_text=query_text,
            query_type=query_type,
            norm_number=classification.detected_norm,
            article_number=classification.detected_article.replace("artículo ", "").replace("articulo ", "") if classification.detected_article else "",
            file_number=classification.detected_norm if classification.detected_norm and "/" in classification.detected_norm else "",
            document_type="",
            jurisdiction=classification.detected_jurisdiction,
            authority=classification.detected_authority,
            temporal=temporal,
            top_k=10,
            min_score=0.1,
        )

    def _parse_as_of(self, classification: QueryClassification) -> tuple[Any, str]:
        """Fecha as_of de la clasificación (None si la consulta no es temporal)."""
        from datetime import date as _date

        hint = classification.temporal_hint
        if not hint.startswith("as_of:"):
            return None, ""
        try:
            return _date.fromisoformat(hint[6:]), classification.temporal_precision
        except ValueError:
            return None, ""

    def _historical_version_guard(
        self, verification: VerificationResult, as_of: Any
    ) -> str | None:
        """Guard: ¿puede el texto consolidado responder a la fecha as_of?

        Para cada cita construida, resuelve el artículo en el corpus
        canónico y escanea sus marcadores de modificación con fecha
        efectiva POSTERIOR a as_of. Si existe uno, el texto consolidado
        NO representa la versión aplicable a la fecha → abstención con
        causa explícita. Sentencias (0 artículos) se excluyen.
        """
        from albra.knowledge.temporal import extract_modification_years

        for cit in self._build_citations(verification)[:5]:
            if cit.document_type in ("sentencia", "auto"):
                continue
            doc_name = cit.citation_text.split(",")[0].strip()
            art = ""
            if "art." in cit.citation_text:
                art = cit.citation_text.rsplit("art.", 1)[-1].strip()
            text = self.citation_auditor.get_article_text(
                document_name=doc_name, article_number=art or None
            )
            if not text:
                continue
            for mod in extract_modification_years(text):
                eff = mod.get("fecha_efectiva", "")
                eff_year = int(eff[:4]) if eff and eff[:4].isdigit() else mod.get("anio_ley", 0)
                if eff_year and eff_year > as_of.year:
                    return (
                        f"La versión del artículo citado ({cit.citation_text}) cambió "
                        f"DESPUÉS de la fecha consultada: {mod['referencia']} "
                        f"(efectiva: {eff}). El corpus indexa el texto consolidado "
                        f"actual, no la versión aplicable a {as_of.isoformat()}. "
                        "Se abstiene de presentar el texto actual como texto "
                        "histórico (cero autoridad fantasma). Requiere ingesta de "
                        "versiones históricas o revisión humana."
                    )
        return None

    def _build_citations(self, verification: VerificationResult) -> list[Citation]:
        """Construye citas formales de la evidencia verificada."""
        citations: list[Citation] = []
        for c in verification.candidates:
            citations.append(Citation(
                document_id=c.document_id,
                source_tier=c.source_tier.name,
                authority=c.authority,
                document_type=c.document_type,
                citation_text=c.citation,
                snippet=c.snippet[:300],
                effective_from=str(c.provenance.get("effective_from", "")) or None,
                effective_until=str(c.provenance.get("effective_until", "")) or None,
                status=c.provenance.get("status", "vigente"),
                source_url=c.provenance.get("source_url", ""),
                is_current=c.is_current,
                content_hash=c.provenance.get("content_hash", ""),
            ))
        return citations

    def _build_response_blocks(
        self,
        query_text: str,
        classification: QueryClassification,
        verification: VerificationResult,
        citations: list[Citation],
    ) -> list[LegalResponseBlock]:
        """Construye bloques de respuesta tipados."""
        blocks: list[LegalResponseBlock] = []

        if not verification.candidates:
            # Should have been caught by abstention
            blocks.append(LegalResponseBlock(
                content_type="abstencion",
                text="No se encontró evidencia jurídica suficiente para esta afirmación.",
                confidence=0.0,
            ))
            return blocks

        # P0 FIX: Use verification.primary_evidence_id — NOT candidates[0]
        # If primary_evidence_id is None or not found → fail-closed (abstention)
        primary = None
        if verification.primary_evidence_id:
            primary = next(
                (c for c in verification.candidates if c.source_id == verification.primary_evidence_id),
                None,
            )
        if primary is None:
            # FAIL-CLOSED: no primary evidence identified
            blocks.append(LegalResponseBlock(
                content_type="abstencion",
                text="No se pudo identificar la evidencia primaria. No se emitirá una afirmación sin verificación.",
                confidence=0.0,
            ))
            return blocks

        blocks.append(LegalResponseBlock(
            content_type="texto_normativo" if primary.document_type in ("ley", "decreto", "codigo", "estatuto", "constitucion") else "jurisprudencia" if primary.document_type in ("sentencia", "auto") else "doctrina",
            text=primary.snippet,
            citations=[c for c in citations if c.document_id == primary.document_id],
            confidence=min(1.0, primary.score + 0.3),
        ))

        # If conflicts, mention them
        if verification.conflicts:
            for conflict in verification.conflicts:
                blocks.append(LegalResponseBlock(
                    content_type="interpretacion",
                    text=f"Conflicto detectado: {conflict.description}",
                    confidence=0.5,
                    needs_review=True,
                ))

        return blocks

    def _audit_citations_pre_reveal(
        self,
        citations: list[Citation],
        verification: VerificationResult,
    ) -> dict[str, Any]:
        """Auditoría fail-closed de las citas de la respuesta.

        Diferenciación de garantías:
        - extracción: aquí no aplica (las citas no se extraen del texto
          con patrones; se construyen desde la evidencia recuperada).
        - validación documental: documento + artículo existen en el
          corpus canónico (``validate_citation_direct``).
        - fidelidad: el snippet recuperado se retraza literalmente en la
          fuente (``literal_retraced``); si no aparece, la cita queda
          ``document_only`` (documento verificado, paráfrasis NO
          demostrada) y se reporta como tal.
        """
        checked: list[dict[str, Any]] = []
        unverified_reasons: list[str] = []
        fidelity_counts: dict[str, int] = {}
        # Mapa document_id → candidate para resolver el nombre de
        # documento según el TIPO (norma: number/title; sentencia:
        # file_number en provenance — la citation_text de jurisprudencia
        # empieza por la corte, no por el documento).
        cand_by_id = {c.document_id: c for c in verification.candidates}
        for cit in citations:
            cand = cand_by_id.get(cit.document_id)
            doc_name = ""
            art = None
            if cand is not None and cand.document_type in ("sentencia", "auto"):
                file_number = str(cand.provenance.get("file_number", "") or "")
                if file_number:
                    doc_name = f"Sentencia {file_number}"
            if not doc_name:
                # Norma: "Constitución Política de 1991, art. 25".
                doc_name = cit.citation_text.split(",")[0].strip()
                if "art." in cit.citation_text:
                    art = cit.citation_text.rsplit("art.", 1)[-1].strip()
            in_corpus, fidelity, reason = self.citation_auditor.validate_citation_direct(
                document_name=doc_name,
                article_number=art,
                snippet=cit.snippet,
            )
            fidelity_counts[fidelity or "unverified"] = fidelity_counts.get(fidelity or "unverified", 0) + 1
            checked.append({
                "citation_text": cit.citation_text,
                "document_id": cit.document_id,
                "in_corpus": in_corpus,
                "fidelity": fidelity,
                "reason": reason,
            })
            if not in_corpus:
                unverified_reasons.append(f"{cit.citation_text}: {reason}")
        all_verified = len(citations) > 0 and not unverified_reasons
        return {
            "executed": True,
            "corpus_version": self.citation_auditor.corpus_version,
            "citations_checked": len(citations),
            "all_verified": all_verified,
            "unverified": len(unverified_reasons),
            "fidelity": fidelity_counts,
            "detail": checked,
            "reason": "; ".join(unverified_reasons) if unverified_reasons else (
                f"{len(citations)} citas verificadas contra corpus canónico."
            ),
            # Nota honesta: la fidelidad de paráfrasis NO se demuestra;
            # solo retracing literal (ver fidelity por cita).
            "paraphrase_verified": False,
        }

    def _analysis_block(self, analysis: LegalAnalysis) -> LegalResponseBlock:
        """Bloque de respuesta con el análisis jurídico estructurado.

        content_type="interpretacion" (tipo marcado del schema): es
        interpretación del sistema, NO texto normativo literal. La cita
        primaria acompaña al bloque.
        """
        a = analysis
        parts: list[str] = []
        parts.append("HECHOS DECLARADOS: " + (" | ".join(a.hechos_declarados[:1]) or "n/d"))
        if a.inferencias:
            parts.append("INFERENCIAS (marcadas): " + " | ".join(a.inferencias))
        if a.problemas_juridicos:
            parts.append("PROBLEMAS JURÍDICOS: " + " | ".join(a.problemas_juridicos))
        if a.hechos_faltantes:
            parts.append("HECHOS FALTANTES: " + " | ".join(a.hechos_faltantes))
        if a.normas_aplicables:
            parts.append("NORMAS APLICABLES: " + " | ".join(
                n["citation"] for n in a.normas_aplicables
            ))
        if a.jurisprudencia_pertinente:
            parts.append("JURISPRUDENCIA PERTINENTE: " + " | ".join(
                j["citation"] for j in a.jurisprudencia_pertinente
            ))
        for arg in a.argumentos:
            parts.append(
                f"ARGUMENTO ({arg.basis}) con cita [{', '.join(c.citation_text for c in arg.citations)}]: "
                f"{arg.claim[:220]}"
            )
        if a.contraargumentos:
            parts.append("CONTRAARGUMENTOS: " + " | ".join(a.contraargumentos))
        if a.riesgos:
            parts.append("RIESGOS: " + " | ".join(a.riesgos))
        parts.append("CONCLUSIÓN: " + a.conclusion)
        primary_citations = [
            c for arg in a.argumentos for c in arg.citations
        ][:2]
        return LegalResponseBlock(
            content_type="interpretacion",
            text="\n".join(parts),
            citations=primary_citations,
            confidence=1.0 if a.conclusion_con_soporte else 0.3,
            needs_review=not a.conclusion_con_soporte,
        )

    def stats(self) -> dict[str, Any]:
        provider_stats = self.retriever.provider.stats()
        articles = int(provider_stats.get("articles", 0) or 0)
        return {
            "retriever": provider_stats,
            "engine": "LegalKnowledgeEngine V1.1",
            "jurisdiction": "CO",
            "abstention_threshold": self.abstention_policy.CONFIDENCE_THRESHOLD,
            # Readiness del servicio jurídico (visibilidad de estado
            # degradado — hallazgo 9 del cierre): un provider sin corpus
            # NO se anuncia disponible; el fail-closed de respuesta
            # (abstención) opera igual en ambos estados.
            "corpus_available": articles > 0,
            "legal_service": (
                "READY" if articles > 0 else "DEGRADED_NO_CORPUS"
            ),
        }
