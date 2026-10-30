# REGISTRO DE AUDITORÍAS — ABOGADO-BASE

**Regla:** los estados que siguen describen lo que dicen los documentos fuente; no certifican que las pruebas se hayan vuelto a ejecutar sin evidencia.

## A-ABOGADO-BASE-001 — Auditoría de extracción Fase 2

- **Fecha:** 2026-10-30
- **Alcance:** Extracción del agente jurídico de DESPACHO-JURIDico commit `fe9d80e` a ABOGADO-BASE.
- **Auditor:** ALBRA Constructor (auto-auditoría para el commit inicial ABOGADO-BASE).

### Verificaciones realizadas

| # | Verificación | Estado | Evidencia |
|---|---|---|---|
| 1 | Clone ABOGADO-BASE exitoso | VERIFIED | `git clone https://github.com/ALBRA8/ABOGADO-BASE.git` — empty repo, branch main |
| 2 | Remote URL limpio (sin PAT) | VERIFIED | `git remote set-url origin https://github.com/ALBRA8/ABOGADO-BASE.git` |
| 3 | Commit de origen = fe9d80e | VERIFIED | `git -C DESPACHO-JURIDico rev-parse HEAD` = `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73` |
| 4 | Componentes lawyer copiados | VERIFIED | `ls albra/lawyer albra/knowledge albra/evidence albra/reasoning albra/playbooks albra/research albra/agents albra/eval` |
| 5 | Núcleo compartido copiado | VERIFIED | `ls albra/identity albra/runtime albra/llm albra/providers albra/memory albra/tools albra/capabilities albra/config albra/observability albra/doctor albra/events albra/handoffs albra/resilience albra/mcp albra/security albra/comms albra/multimodal albra/files albra/workflows` |
| 6 | Audit-core copiado (sin matter_audit) | VERIFIED | `ls albra/audit/` = `__init__.py install_log.py log.py tamper_evident.py` (NO `matter_audit.py`) |
| 7 | src/ copiado (AGENTE-GENERAL + arnés) | VERIFIED | `ls src/adapters/general_adapter.py src/harness/ src/bridges/ src/bootstrap/` |
| 8 | Corpus V1.4 copiado | VERIFIED | `ls albra/knowledge/colombia/corpus_pilot/v14_raw/` con 5 dirs + sentencias |
| 9 | Tests lawyer copiados | VERIFIED | `ls tests/lawyer tests/knowledge tests/agents tests/playbooks tests/reasoning tests/eval tests/harness` |
| 10 | Tests compartidos copiados | VERIFIED | `ls tests/llm tests/mcp tests/memory tests/identity tests/observability tests/security` |
| 11 | Tests con deps oficina removidos | VERIFIED | `grep -rl "from albra.matters\|from albra.audit.matter_audit" tests/` = 0 resultados |
| 12 | Sin imports oficina en albra/ | VERIFIED | `grep -rn "from albra.matters\|from albra.marketplace\|from albra.whitelabel\|from albra.scheduling\|from albra.documents\|from albra.review\|from albra.api\b\|from albra.audit.matter_audit\|from albra.cli\b" albra/ src/` = 0 resultados |
| 13 | Identidad renombrada (D1) | VERIFIED | `grep "ABOGADO BASE ALBRA\|ALBRA-ABOGADO-V1\|ABOGADO BASE INDEPENDIENTE" albra/identity/manifest.py` |
| 14 | pyproject.toml renombrado | VERIFIED | `name = "abogado-base"`, `version = "1.0.0"` |
| 15 | README creado | VERIFIED | `README.md` documenta origen, identidad, componentes, limitaciones |
| 16 | CONTEXTO/CURRENT_STATE.md creado | VERIFIED | Documenta origen, ajustes, limitaciones heredadas |
| 17 | CONTEXTO/REGISTRO_DECISIONES.md creado | VERIFIED | D-ABOGADO-BASE-001 APPROVED |
| 18 | __pycache__/.pyc limpiados | VERIFIED | `find . -name __pycache__ -type d` = 0 resultados |
| 19 | DESPACHO-JURIDico intacto | VERIFIED | `git -C DESPACHO-JURIDico status --short` = vacío, HEAD = `fe9d80e` |
| 20 | Push NO realizado | VERIFIED | `git log` ABOGADO-BASE = sin commits remotos; solo commit local pendiente |

### Limitaciones explícitas

- **Fase 3 NO ejecutada.** No se ha verificado que ABOGADO-BASE funcione independientemente (instalación, tests, CI). Pendiente de autorización.
- **Fase 4 NO ejecutada.** DESPACHO-JURIDico permanece intacto con el abogado aún incorporado. Pendiente de autorización.
- **Fase 5 NO ejecutada.** Sin pruebas de separación. Pendiente.
- **Fase 6 NO ejecutada.** Sin cierre documental de la separación. Pendiente.
- **MCP server con stubs:** `_tenant_is_authorized`, `_matter_store`, `_audit_chain` retornan False/None. El abogado no gestiona matters — si se invoca una tool de matters, fallará con error. Esto es aceptable porque las tools de matters son del despacho.
- **Núcleo compartido duplicado:** el costo de independencia es que identity/runtime/security/mcp/llm/etc. están copiados en ambos repos. Mantenimiento duplicado.

### Dictamen

FASE 2 — EXTRACCIÓN ABOGADO-BASE: COMPLETADA sin push.

- Commit inicial creado localmente en ABOGADO-BASE.
- DESPACHO-JURIDico permanece exactamente como estaba (HEAD `fe9d80e`, working tree limpio).
- Sin modificaciones al repositorio de origen.
- Sin commits ni pushes al remoto ABOGADO-BASE.
- Fases 3, 4, 5, 6 NO ejecutadas — pendientes de autorización expresa.

---

## A-ABOGADO-BASE-002 — Cierre funcional del abogado (PROMPT MAESTRO)

- **Fecha:** 2026-10-30
- **Alcance:** Cierre funcional del ABOGADO ALBRA — consolidación del motor jurídico existente sobre `feat/seed-parity`.
- **SHA inicial:** `6e936e16a5a9deee3c6776f77be9a4e5a11be1d8`
- **SHA final:** (ver commit de cierre — registrado al final de esta entrada)
- **Auditor:** ALBRA Constructor (auto-auditoría con ejecución real de pruebas).
- **Estado de Git antes de modificar:** rama `feat/seed-parity`, working tree limpio, HEAD = SHA inicial (verificado: sin cambios respecto a la referencia).

### Método

Comparación componente a componente con el origen (`ALBRA8/DESPACHO-JURIDICO`, clon de solo lectura en HEAD `d839eb0`) antes de cada cambio; recuperación/conexión/completitud de capacidades existentes; NINGÚN motor nuevo; NINGÚN componente reemplazado sin demostrar la necesidad.

### Hallazgos y cambios

| # | Hallazgo | Archivo(s) afectado(s) | Implementación original | Cambio realizado | Justificación | Prueba que demuestra el cierre |
|---|---|---|---|---|---|---|
| 1 | P0-3: no existía prueba integral del agente (la original vive en DESPACHO `tests/test_agent_integration.py`) | `tests/test_agent_integration.py` (nuevo) | Test de 8 casos en DESPACHO sin sembrado de corpus ni verificación de provenance | Prueba integral equivalente y extendida: `Agent.boot()` → corpus_seed → LegalKnowledgeEngine → Runtime → `Agent.process()` con verificación de 12 docs / 2.200 arts, seed_failed=False, enrutamiento real, evidencia+cita+provenance+hash, abstención, contrato de veredicto, apagado limpio, boot degradado explícito | La cobertura original no se migró al extraer; la prueba integral es el criterio de "agente que funciona", no "módulos que importan" | 10 tests en la suite (pasa en py3.10/3.11/3.12) |
| 2 | P0-4a: consultas por TÍTULO de norma caían a 0 hits y abstenían espuriamente (p.ej. CST art. 23) | `albra/knowledge/retrieval_providers.py` | `_exact_search` solo comparaba contra `norm.number` | Compara contra number Y title (ambos metadatos indexados por el clasificador/ingesta) | Desconexión clasificador→retrieval: el clasificador emite el título detectado ("Código Sustantivo del Trabajo"), el number es "Decreto 2663 de 1950" | `test_agent_integration.py::test_agent_cst_article_recovered_after_connection_fix`; verificado manualmente: 0 hits antes, evidencia literal_retraced después |
| 3 | P0-4b: la respuesta del engine era solo el fragmento recuperado (sin análisis jurídico) | `albra/knowledge/legal_reasoning.py` (nuevo), `albra/knowledge/legal_engine.py`, `albra/knowledge/citation.py` | Pipeline terminaba en el bloque normativo | Análisis jurídico estructurado DETERMINISTA sobre la evidencia ya verificada: hechos declarados vs inferencias vs conclusión, problemas jurídicos, hechos faltantes, normas aplicables, jurisprudencia pertinente, contrastación (conflictos del verifier), argumentos CON cita por afirmación, contraargumentos y riesgos (conflictos, evidencia no vigente, tiers no primarios), conclusión con/sin soporte | Completar la capacidad de análisis con componentes existentes (classifier + verifier + conflicts + vigencia); sin LLM: el razonamiento de un proveedor nunca sustituye la verificación de fuentes | `tests/knowledge/test_legal_reasoning.py` (5 tests) + bloque `interpretacion` en toda respuesta no-abstenta |
| 4 | P1-5: LawyerExam recibía `legal_issues`/`required_sources` externos y abstenía sin ellos | `albra/lawyer/exam.py` (pasos 3, 4, 5, 6, 7, 10), `albra/lawyer/issue_discovery.py` (nuevo) | Pasos 3-4 tomaban los datos del caso; sin ellos → ABSTAINED (paso 3) | El agente PROPONE problemas jurídicos y fuentes deterministamente desde los hechos (`LegalQueryClassifier` + dominios derivados de los títulos del corpus canónico). Toda propuesta marcada `proposed_by_agent=True`/`verified=False`; pasos 5-6 la contrastan contra el corpus; no encontrada → `sin_verificar: True` explícito | Completar la identificación de issues y propuesta de fuentes; conservar 12 pasos, RealProviderGuard, AdversarialValidator, revisión humana y abstención | `tests/lawyer/test_exam_issue_discovery.py` (9 tests); regresión V7.0 intacta (277 tests lawyer+knowledge) |
| 5 | P1-6: `legal_verdict="APPROVED"` fijo coexistiendo con `abstention=True` | `albra/runtime/engine.py` | Asignación literal `"APPROVED"` en la ruta legal | Contrato separado: `legal_gate` (autorización, veredicto del LegalGate) ≠ `legal_verdict` (resultado: ANSWERED_WITH_EVIDENCE / ABSTAINED / NEEDS_HUMAN_REVIEW / GATE_BLOCKED); `needs_hitl` expuesto; sin consumidores que dependan de "APPROVED" (grep verificado) | No presentar una autorización de ejecución como aprobación jurídica; cambio de contrato documentado y probado | `tests/runtime/test_legal_verdict_contract.py` (4 tests) |
| 6 | Hallazgo 7: auditoría de citas solo ejecutaba en exam/eval y contra V1.1 (12 arts), no contra el corpus canónico | `albra/knowledge/citation_audit.py`, `albra/knowledge/legal_engine.py`, `albra/lawyer/exam.py` | `CitationAuditor()` default v11; engine SIN auditoría pre-reveal; exam con auditor v11 | (a) nueva versión `v14` = corpus canónico V1.4+V1.3 vía `canonical_corpus_documents()`; índice por number Y title; resolución de sentencias "Sentencia T-001/2020"→"T-001-2020"; patrón Decreto añadido; (b) `validate_citation_direct()` para citas construidas programáticamente; (c) TODA respuesta no-abstenta del engine audita sus citas ANTES de revelarse — 1 cita no verificada → abstención (fail-closed); (d) fidelidad diferenciada: `document_only` vs `literal_retraced`; `paraphrase_verified: False` honesto; exam usa v14 | Alinear validación con el corpus canónico; bloquear citas no verificadas en rutas fail-closed; nunca declarar verificada una paráfrasis | `tests/knowledge/test_citation_audit_v14.py` (13 tests) + `citation_audit` en cada respuesta del engine |
| 7 | Hallazgo 8: fuentes oficiales declarativas con URL vacía; riesgo de afirmar conectividad inexistente | `tests/knowledge/test_vigency_status_matrix.py` (nuevo) | Catálogo `sources.py` con URLs vacías y comentario honesto; `ingestion_colombia.py` con fetcher real urllib | Sin cambios de código: verificación automática de que (a) el catálogo NO declara URLs sin integración real, (b) el fetcher real de ingestion_colombia existe (infraestructura bajo demanda, NO verificación en tiempo real), (c) los 10 VALIDITY_STATUS se distinguen (vigente/derogada/modificada/sustituida/suspendida/inexequible/nula/perdida_vigencia/historica/pendiente), (d) vigencia histórica/as_of opera | No inventar fuentes ni vigencia; no afirmar comprobación en tiempo real sin integración real | 21 tests de la matriz de vigencia/fuentes |
| 8 | Hallazgo 9: éxito de siembra no reportaba `seed_failed`; estado degradado sin sonda de readiness | `albra/knowledge/corpus_seed.py`, `albra/knowledge/legal_engine.py`, `albra/doctor/builtin_checks.py` | `as_dict()` sin la clave; degraded solo en boot del agente; doctor sin check jurídico | (a) `seed_failed: False` explícito en el reporte exitoso (contrato: la clave SIEMPRE existe); (b) `engine.stats()` reporta `corpus_available` y `legal_service` (READY / DEGRADED_NO_CORPUS); (c) check `legal_knowledge` en el doctor: sonda REAL (hashes del corpus + abstención sin corpus + readiness del servicio) | El estado degradado debe ser visible; el servicio jurídico no se anuncia saludable sin corpus | `test_agent_integration.py::test_agent_boot_seeds_canonical_corpus` + `::test_agent_degraded_seed_is_explicit`; doctor check ejecutable con `albra doctor` |
| 9 | P0-4c: fallback `rules_fallback_legal` del ReasoningEngine con mensaje STALE ("conocimiento jurídico aún no cargado") | `albra/reasoning/engine.py` (SIN CAMBIO — documentado como limitación) | Mensaje de la V1.6 previa a la migración del corpus | No se modificó: esa ruta solo se alcanza cuando `_is_legal_query` clasifica la consulta como NO jurídica y el intent del reasoning como legal_question; es un camino de borde que no afecta la ruta real (legal → engine). Ajustar el texto del fallback es un cambio cosmético que puede hacerse sin prisa | Minimizar el diff en el cierre; el mensaje stale no produce afirmaciones jurídicas (produce abstención informativa) | N/A — registrado como limitación restante |

### Comparación con DESPACHO-JURIDICO

- `tests/test_agent_integration.py` original (DESPACHO@HEAD, 98 líneas): 8 tests; ninguno verifica sembrado de corpus, provenance, ni contrato de veredicto. La versión ABOGADO-BASE cubre y extiende todo el recorrido con corpus real.
- No se trasladó ninguna función administrativa del despacho (matters/marketplace/whitelabel/scheduling/documents/review/api/cli): grep de imports de oficina = 0 resultados en `albra/` y `src/` (sin cambios respecto a la auditoría 001).
- DESPACHO-JURIDICO: NO modificado (solo lectura; HEAD `d839eb0` intacto al cierre).

### Estados de implementación (distinción exigida)

| Componente | Implementado | Probado unitariamente | Probado E2E | Verificado en CI | Preparado para despliegue | Desplegado en producción |
|---|---|---|---|---|---|---|
| Siembra de corpus (corpus_seed) | SÍ (b508128) | SÍ | SÍ (boot real) | SÍ (suite local; CI al push) | SÍ | NO |
| Retrieval exacto por título (conexión) | SÍ (este cierre) | SÍ | SÍ (Agent.process) | SÍ (local) | SÍ | NO |
| Análisis jurídico estructurado (legal_reasoning) | SÍ (este cierre) | SÍ | SÍ (Agent.process) | SÍ (local) | SÍ (con limitaciones NLI documentadas) | NO |
| Auditoría de citas v14 + fail-closed pre-reveal | SÍ (este cierre) | SÍ | SÍ (Agent.process) | SÍ (local) | SÍ | NO |
| Contrato legal_verdict/legal_gate | SÍ (este cierre) | SÍ | SÍ (Agent.process) | SÍ (local) | SÍ | NO |
| Autonomía de LawyerExam (issues+fuentes propuestas) | SÍ (este cierre) | SÍ | SÍ (examen completo con LLM real NO ejecutado — sin API key) | SÍ (local) | Parcial (borrador requiere revisión humana por diseño) | NO |
| Vigencia (10 estados + histórica + as_of) | SÍ (existente) | SÍ (matriz nueva) | Parcial (sin corpus de normas derogadas reales en el índice) | SÍ (local) | Parcial | NO |
| Fuentes oficiales | Declarativo (existente) | SÍ | Fetch real NO ejecutado en CI (red) | N/A | NO (URLs pendientes de integración) | NO |
| Fidelidad de paráfrasis semántica (NLI) | NO (limitación heredada V8.0) | N/A | N/A | N/A | NO | NO |

### Ejecución de pruebas (evidencia)

| Entorno | Resultado |
|---|---|
| Suite completa py3.12 (venv del repo) | 1221 passed, 11 skipped |
| Suite completa py3.10 (uv venv limpio) | 1221 passed, 11 skipped |
| Suite completa py3.11 (uv venv limpio) | 1221 passed, 11 skipped |
| Ruff (albra/ tests/ src/ — targets de CI) | All checks passed |
| Clean-room (clone del SHA final + pip install -e .[dev] + suite) | ver REGISTRO al final / informe final |
| Prueba integral del agente (10 tests) | passed (incluye boot degradado simulado) |

### Limitaciones restantes (honestas)

1. **Fidelidad de paráfrasis semántica (NLI)**: NO implementada (heredada de V8.0 Fase 4). El sistema marca `document_only` y `paraphrase_verified: False`; nunca declara verificada una paráfrasis.
2. **Examen completo con LLM real**: no ejecutado en este cierre (requiere NVIDIA_API_KEY); los pasos 7-11 quedan probados por estructura + guard (MockProvider → BLOCKED) y por los tests V7.0/V8.0 existentes.
3. **Fallback stale del ReasoningEngine** (ver hallazgo 9): mensaje cosmético desactualizado en un camino de borde; sin efecto en la ruta real legal→engine.
4. **Fuentes oficiales**: catálogo declarativo sin integración real; fetch bajo demanda existe (ingestion_colombia) pero no hay verificación en tiempo real de vigencia.
5. **Vigencia parcial**: el índice solo contiene las normas del corpus canónico (7 normas + 5 sentencias); la vigencia de normas FUERA del corpus queda UNKNOWN/uncertain por diseño.
6. **Push/CI**: este cierre NO hace push ni merge ni release (sin autorización expresa); la verificación de CI en GitHub Actions del SHA final queda pendiente de autorización de push.

### Registro del SHA final

- **SHA final:** el commit de cierre es el HEAD de `feat/seed-parity` tras esta entrada (el SHA exacto se documenta en el informe final, que vive fuera del repositorio; un SHA no puede autocontenerse). Commit: "feat: cierre funcional del abogado — análisis jurídico, contrato de veredicto, autonomía de exam, auditoría v14, readiness".
- **Estado:** working tree limpio; sin push/merge/release.
- **Clean-room:** clon del SHA final + `pip install -e ".[dev]"` + suite completa (resultado en el informe final).

---

## A-ABOGADO-BASE-003 — Fase Producción Real (PROMPT MAESTRO: de agente técnicamente preparado a agente jurídico apto para servicio real)

- **Fecha:** 2026-10-30
- **SHA inicial:** `ef3681020957cbb93107ba54c1290fa30acd334f` (cierre funcional, CI remoto verde, push autorizado)
- **Auditor:** ALBRA Constructor (auto-auditoría con ejecución real y batería adversarial).
- **Estado de Git antes de modificar:** rama `feat/seed-parity`, HEAD = SHA inicial, working tree sin cambios de contenido.

### FASE 0 — Auditoría de producción (hallazgos que motivaron los cambios)

| # | Hallazgo | Evidencia |
|---|---|---|
| T1 | Corpus canónico limitado a 12 documentos (2.200 arts): sin civil, penal sustantivo, CPACA, comercio, seguridad social completa, contratación completa | inventario `canonical_corpus_documents()` |
| T2 | Consultas históricas rotas: "¿qué decía el art. X el 15-03-2018?" abstenía (el clasificador no parseaba la fecha) y "hechos de 2015" se clasificaba `current` — riesgo de usar texto actual para hechos históricos | ejecución viva; `query_classifier.py:202-210` |
| T3 | `RealProviderGuard.is_real()` tenía un try/except MUERTO: documentaba una sonda health-check y ejecutaba `return True` | `real_provider_guard.py:88-96` |
| T4 | `get_default_router()` no exponía el proveedor real (nvidia ausente de `_PROVIDER_CLASSES`) | `router.py:52-57` |
| T5 | Calidad de datos: el extractor DESTRUYA las notas editoriales de modificación `<Artículo subrogado/modificado por...>` (las confundía con tags HTML) — la evidencia de vigencia era invisible (86 mods detectadas vs 406 reales); 1 artículo fantasma en Ley 640 (referencia en prosa capturada como artículo) | reconstrucción desde raw_bytes preservados |
| T6 | Keyword matching por substring: "comercIA**ntes**" contenía "antes" → hints históricos espurios | batería adversarial |
| T7 | Fuentes oficiales: catálogo declarativo sin distinción REGISTERED/FETCHABLE/VERIFIED/CURRENT | `sources.py` |

### Cambios realizados (componente a componente, sin arquitectura paralela)

| Componente | Cambio | Prueba |
|---|---|---|
| Corpus V1.5 (NUEVO) | 6 normas completas ingeridas de secretariasenado.gov.co (Código Civil 2673, Código Penal 598, CPACA 321, Comercio 2037, Ley 100 completa 296, Ley 80 completa 83) + 5 sentencias reales de corteconstitucional.gov.co (T-760/08, SU-360/99, C-355/06, C-239/97, C-075/07). raw_bytes preservados (v15_raw/, 33 MB) + SHA-256 por página + timestamps. Same-method que V1.4 | `tests/knowledge/test_corpus_v15.py` (15 tests) |
| corpus_seed | Canónico = V1.5+V1.4 (21 docs / 8114 arts / 10 sentencias); subsumpción de fragmentos V1.3 de Ley 100/80; enriquecimiento de jurisprudencia con metadatos reales | `test_corpus_seed.py` |
| `official_sources.py` (NUEVO) | Capa Official Source: estados demostrables SOURCE_REGISTERED/FETCHABLE/VERIFIED/CURRENT/CHANGED/UNREACHABLE con evidencia (manifests); `reverify()` re-consulta y compara hash — SOURCE_CURRENT demostrado EN VIVO contra la fuente (T-760/08 y C-239/97, 2026-10-30T22:26Z) | `test_official_sources.py` (7) |
| `coverage_plan.py` (NUEVO) | Matriz de cobertura por dominio/subdominio/fuente/norma con estados honestos (PRESENT_FULL solo con corpus ingerido; ABSENT_BLOCKED/DECISION/PLANNED documentados) | `test_coverage_plan.py` (6) |
| `temporal.py` | `parse_temporal_reference()` (fechas exactas en español; años aproximados DECLARADOS; "Ley 100 de 1993" NO es fecha) + `extract_modification_years()` (marcadores con fecha efectiva) | `test_temporal_production.py` |
| `query_classifier.py` | as_of exacto/approx + precisión declarada; lookahead de norma termina en fechas/"cuando"; keywords con límite de palabra (fix "comercIAntes") | id. |
| `legal_engine.py` | Guard de versión histórica: si un artículo citado cambió DESPUÉS de la fecha consultada → ABSTENCIÓN con causa (nunca texto consolidado como histórico); si no cambió → respuesta con CONTEXTO TEMPORAL explícito | `test_temporal_production.py` (E2E) |
| V1.4/V1.5 extractor | Pattern case-sensitive (headers MAYÚSCULAS vs referencias en prosa) + protección de notas editoriales 【...】 → 406 artículos con evidencia real de modificación en V1.4; eliminado el artículo fantasma (2107→2106) | `test_v80_fase4_vigency_false_positives.py` |
| `retrieval_providers.py` | Niveles TEST/BOOTSTRAP/PRODUCTION: InMemory=BOOTSTRAP explícito; fábrica fail-closed para PRODUCTION (persistente no implementado — nunca memoria disfrazada de producción) | `tests/llm/test_production_phase_guards.py` |
| `real_provider_guard.py` | Sonda REAL de salud (`probe()`) con matriz MOCK/SCAFFOLD_NOT_CONFIGURED/REAL_HEALTHY/REAL_UNAVAILABLE/REAL_FAILED (cacheada); try/except muerto eliminado; `require_real(probe_health=True)` | id. (13) |
| `router.py` | nvidia en el mapa + construcción con fallo contenido (`_provider_errors`) — el router arranca sin credenciales y registra la causa | `tests/llm/` |
| `jurisprudence_metadata.py` (NUEVO) | Metadatos reales de las 10 sentencias extraídos del texto (9/10 fechas, 8/10 ponentes, 5/10 expedientes, 6/10 salas; lo ausente queda None); clasificación de precedente (VERIFICADA/VINCULANTE/PERSUASIVA/CONTRADICTORIA/NO_VERIFICADA) | `test_jurisprudence_metadata.py` (10) |
| `response_policy.py` (NUEVO) | Política HITL determinista: ANSWER / ANSWER_WITH_WARNING / ABSTAIN / HUMAN_REVIEW_REQUIRED con precedencia protectora | `tests/legal_battery/` |
| `eval/legal_rubric.py` (NUEVO) | Rúbrica de abogado: 14 dimensiones; hallucinated legal authority ⟹ FAIL | id. |
| `doctor/builtin_checks.py` | Sonda legal_knowledge con conteo canónico dinámico | suite doctor |

### Batería de casos (FASE 7) y adversarial (FASE 8)

- **Batería 8/8 dominios** (civil, laboral, penal, procesal, administrativo, constitucional, comercial, seguridad social): todos responden con evidencia `literal_retraced` y auditoría en verde (`tests/legal_battery/test_case_battery.py`).
- **Adversarial 12/12 bloqueado correctamente**: norma inventada→abstención; sentencia inexistente→abstención; versión cambiada→guard; artículo inexistente→abstención; jurisdicción extranjera→abstención; fecha anterior→abstención; cita falsa→fidelity degradada; hipótesis≠hecho; consulta vacía→abstención; precedente conflictivo→CONTRADICTORIA; gate no evadible; fuente REGISTERED nunca VERIFIED (`tests/legal_battery/test_adversarial.py`).

### Bloqueos documentados (no ocultados)

1. **LLM real no ejecutado**: sin NVIDIA_API_KEY en el entorno. El camino real existe (NVIDIAProvider + guard + health probe) y falla cerrado; los pasos 7-11 del examen siguen probados por estructura y guard (Mock→BLOCKED).
2. **NLI de paráfrasis**: no implementada (heredada V8.0); `paraphrase_verified: False` honesto.
3. **Retrieval persistente (PRODUCTION tier)**: no implementado; la fábrica falla cerrado.
4. **Cobertura ausente**: familia especial (Ley 1098/2006 — bloqueo de red en los intentos de la fase), CSJ (relatoría js-driven, requiere Playwright), decretos reglamentarios (funcionpublica inalcanzable), tributario (decisión de alcance pendiente).
5. **SU-360/99**: metadatos incompletos (formato de página distinto) — None honesto.
6. **CI/clean-room del nuevo estado**: pendientes de push autorizado (como en el cierre anterior).

### Ejecución de pruebas (evidencia)

| Entorno | Resultado |
|---|---|
| Suite completa py3.12 (venv del repo) | 1331 collected, 1320 passed, 11 skipped, 0 fallos (+98 tests nuevos) |
| Batería 8 dominios | 8/8 con evidencia literal_retraced |
| Adversarial | 12/12 comportamiento protector correcto |
| Ruff | pendiente de ejecución final (targets de CI) |

### Registro del SHA final

- **SHA final:** el commit de esta fase es el HEAD de `feat/seed-parity` tras esta entrada (el SHA exacto vive en el informe, fuera del repositorio). Commit: "feat: fase producción real — corpus V1.5 (21 docs/8114 arts), fuentes oficiales demostrables, vigencia real con guard histórico, jurisprudencia con metadatos, batería+adversarial, rúbrica y política HITL".
- **Estado:** working tree limpio tras commit; sin push/merge/release/despliegue (requieren autorización).
- **Dictamen:** CONTROLLED PILOT READY (ver INFORME_PRODUCCION_REAL_ABOGADO_ALBRA.md — la evidencia NO alcanza para PRODUCTION READY: sin LLM real ejecutado, sin retrieval persistente, sin clean-room/CI del nuevo SHA).
