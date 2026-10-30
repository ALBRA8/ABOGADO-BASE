# Corpus Jurídico de ABOGADO-BASE — Estado Real

> Documento generado en la migración de conocimiento DESPACHO-JURIDICO →
> ABOGADO-BASE. Refleja el estado verificado del repositorio, no
> aspiraciones. Los informes históricos del corpus están preservados en
> `docs/corpus/` (copiados textualmente desde el despacho como traza de
> provenance documental).

## 1. Qué posee el abogado

`ABOGADO-BASE` es el **propietario físico y funcional** de su conocimiento
jurídico. Todo vive dentro de este repositorio:

```
albra/knowledge/                      # 129 ficheros — motor de conocimiento
├── legal_engine.py                   #   LegalKnowledgeEngine (órgano del runtime)
├── retrieval.py / retrieval_providers.py  # HybridRetriever + backends
├── ingestion.py / ingestion_pipeline.py / ingestion_colombia.py
├── citation.py / citation_audit.py / citation_graph.py / agentic_citator.py
├── norm_reference.py / vigency.py / temporal.py / contradiction.py
├── abstention.py / verification.py / query_classifier.py
├── provenance.py / legal_provenance.py / schemas.py / rag_local.py / loader.py
└── colombia/corpus_pilot/
    ├── real_corpus_v11.py … v14.py   # corpus estructurado (versionado)
    ├── constitution/ legislation/ jurisprudence/
    └── v14_raw/                      # raw bytes capturados + manifests con hashes
```

## 2. Corpus canónico sembrado (V1.4 + V1.3 vivas)

| Documento | Versión | Artículos | Fuente oficial |
|---|---|---|---|
| Constitución Política de 1991 (completa) | V1.4 | 380 | secretariasenado.gov.co |
| Ley 1564 de 2012 (CGP) | V1.4 | 627 | secretariasenado.gov.co |
| Ley 640 de 2001 (conciliación) | V1.4 | 50 | secretariasenado.gov.co |
| Ley 906 de 2004 (CPP) | V1.4 | 564 | secretariasenado.gov.co |
| Código Sustantivo del Trabajo (D. 2663/1950) | V1.4 | 467 | secretariasenado.gov.co |
| 5 sentencias Corte Constitucional (T-001, T-002, T-003, T-100, T-445 de 2020) | V1.4 | — | corteconstitucional.gov.co |
| Ley 100 de 1993 | V1.3 | 45 | secretariasenado.gov.co |
| Ley 80 de 1993 | V1.3 | 48 | secretariasenado.gov.co |

**Total sembrado en el retrieval: 12 documentos, 2.200 artículos, 5
jurisprudencias.** Las versiones subsumidas (Constitución V1.1/V1.3, que
sólo traían un subconjunto de artículos) NO se siembran para no duplicar
normas; permanecen en disco como historia del corpus.

## 3. Integridad y provenance

* Cada documento lleva `reconstructed_text_hash` (SHA-256). La siembra
  **verifica el hash ANTES de ingestar**; un documento con hash inválido
  se omite y se reporta (nunca se siembra contenido no verificado).
  Verificación actual: **12/12 OK** (`tests/knowledge/test_corpus_seed.py`).
* V1.4 preserva los **raw bytes** capturados con su manifest por página:
  URL, HTTP status, `raw_bytes_hash`, `retrieval_timestamp`
  (`albra/knowledge/colombia/corpus_pilot/v14_raw/*/manifest.json`).
  Los hashes del manifest coinciden con los bytes en disco (testeado).
* El tipo original del corpus (`codigo_sustantivo`, `jurisprudencia`) se
  conserva en la provenance indexada (`corpus_document_type`); el mapeo
  al esquema de ingesta (`codigo`, `sentencia`) se aplica sólo en la
  llamada y no altera el corpus.
* Las citas construidas por el `LegalKnowledgeEngine` incluyen
  `content_hash` (SHA-256 del contenido citado), `source_url`,
  `source_tier`, autoridad y vigencia.

## 4. La ruta real del conocimiento (verificada)

```
CORPUS EN DISCO (albra/knowledge/colombia/corpus_pilot)
    ↓  albra/knowledge/corpus_seed.py  (verificación de hashes + ingesta)
INGESTIÓN  (LegalIngestionPipeline — abstracciones existentes)
    ↓
RETRIEVAL  (InMemoryRetrievalProvider → HybridRetriever)
    ↓   (boot del agente SIEMBRA el corpus: albra/identity/agent.py)
LEGAL KNOWLEDGE ENGINE  (órgano "legal_engine" del runtime)
    ↓   (albra/runtime/engine.py rutear consultas jurídicas al engine)
ABOGADO  → respuesta con citas, provenance y evidencia registrada
```

Evidencia de extremo a extremo (`tests/knowledge/test_corpus_seed.py::test_engine_e2e_respuesta_con_citas_y_provenance`):

```
Pregunta: "¿Qué establece el artículo 11 de la Constitución Política sobre
           el derecho a la vida?"
→ corpus sembrado en boot: 12 documentos, 0 hashes inválidos
→ LegalKnowledgeEngine (tipo: consulta_normativa, sin abstención)
→ Respuesta: "El derecho a la vida es inviolable. No habrá pena de muerte."
→ Cita: Asamblea Nacional Constituyente
         http://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.htm
         content_hash: SHA-256 del texto citado
```

## 5. Qué NO se migró del despacho (deliberadamente)

Componentes de la OFICINA que no son conocimiento del abogado:
`albra/matters/`, `albra/marketplace/`, `albra/whitelabel/`,
`albra/scheduling/`, `albra/documents/` (redline), `albra/review/`,
`albra/audit/matter_audit.py`, `albra/cli.py` del despacho,
`src/` (harness de la oficina: adapters, bridges ZAI, registries) y sus
tests. El abogado no los necesita para saber derecho (ver
`tests/test_knowledge_independence.py`).

## 6. Limitaciones aceptadas

* El backend de retrieval por defecto es in-memory con embeddings
  hash-based (léxico). Suficiente para el corpus actual y sin dependencias
  externas; un backend SQLite/Qdrant es un reemplazo del provider, no un
  cambio de arquitectura.
* `source_url_authenticated=False` en la provenance de ingesta: la URL es
  válida en formato y proviene de fuentes oficiales S0, pero la
  autenticación criptográfica de la fuente no se realiza en esta fase.
* Los docs históricos en `docs/corpus/` describen estados anteriores del
  corpus (V1.0–V1.2) tal como fueron redactados en su momento; no han sido
  reescritos.
