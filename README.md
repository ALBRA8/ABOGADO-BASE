# ABOGADO BASE ALBRA

**Agente jurídico independiente — V1.0**

## Origen

Este repositorio fue extraído de [`ALBRA8/DESPACHO-JURIDICO`](https://github.com/ALBRA8/DESPACHO-JURIDICO) commit `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73` como parte de la **misión de separación arquitectónica V9.0**.

El objetivo: separar al abogado (agente jurídico) de la oficina (despacho jurídico) para que cada uno viva en su propio repositorio independiente.

- **ABOGADO-BASE** = el agente jurídico independiente (este repositorio).
- **DESPACHO-JURIDICO** = la oficina jurídica (sin el abogado incorporado).

## Identidad

| Campo | Valor |
|---|---|
| Name | `ABOGADO BASE ALBRA` |
| Codename | `ALBRA-ABOGADO-V1` |
| Versión | `1.0.0` |
| Rol | `ABOGADO BASE INDEPENDIENTE ALBRA` |
| Jurisdicción | `CO` (Colombia) |
| Especialización | `generalista-base` (núcleo; especialidades vienen después) |

## Componentes extraídos

### Núcleo del abogado

- **AGENTE-GENERAL** — `src/adapters/general_adapter.py` (el agente intercambiable)
- **Arnés** — `src/harness/` (KnowledgeRegistry + SkillRegistry)
- **Bridges** — `src/bridges/` (IBridge + PythonBridge + ZaiSdkBridge)
- **Bootstrap API** — `src/bootstrap/api/`

### Chaleco jurídico

- **LawyerExam** — `albra/lawyer/exam.py` (12-step exam + draft citation audit Fase 4)
- **AdversarialValidator** — `albra/lawyer/adversarial_validation.py`
- **Knowledge layer** — `albra/knowledge/` (28 módulos: vigency, contradiction, norm_reference, citation_audit, legal_engine, etc.)
- **Corpus V1.4** — `albra/knowledge/colombia/corpus_pilot/` (10 docs, 2107 artículos, hashes SHA-256 verificados)
- **Evidence** — `albra/evidence/` (chain, cite_gate, legal_gate)
- **Reasoning** — `albra/reasoning/` (engine, debate, layers, adversarial_pipeline, precedent_board)
- **Playbooks** — `albra/playbooks/` (civil, constitucional, laboral, penal, corporativo, familia)
- **Research** — `albra/research/` (engine, crag)
- **Agent definitions** — `albra/agents/` (research, filing, review, drafting, intake)
- **Eval suite** — `albra/eval/` (rubrics, runner, phantom_citations, drafting_rubrics)

### Núcleo compartido (necesario para el runtime del agente)

- **Identity** — `albra/identity/` (agent, manifest, organ_manifests, oidc/)
- **Runtime** — `albra/runtime/` (engine, context)
- **LLM** — `albra/llm/` (providers, real_provider_guard, router)
- **Providers** — `albra/providers/` (registry, router, llm, base)
- **Memory** — `albra/memory/` (interface, cell, store, categories, consolidator)
- **Tools** — `albra/tools/` (registry, builtin, base)
- **Capabilities** — `albra/capabilities/` (registry)
- **Config** — `albra/config/` (settings)
- **Observability** — `albra/observability/` (logger, trace, metrics, correlation, execution_trace)
- **Doctor** — `albra/doctor/` (self_healing, diagnostic, self_improve)
- **Events** — `albra/events/` (bus)
- **Handoffs** — `albra/handoffs/` (protocol)
- **Resilience** — `albra/resilience/` (circuit_breaker, fallback, recovery, retry)
- **MCP server** — `albra/mcp/` (server, client, protocol, security, jurisdictions)
- **Security** — `albra/security/` (auth, rbac, oidc, execution_guard, hitl, audit, policy, autonomy, classification, data_boundary, deterministic_guard, firewall, tokens, approval_chain)
- **Comms** — `albra/comms/` (router, base, adapters: telegram, whatsapp, voice, text)
- **Multimodal** — `albra/multimodal/` (document, text, image, audio)
- **Files** — `albra/files/` (tracker)
- **Workflows** — `albra/workflows/` (engine, sops, graph)
- **Audit-core** — `albra/audit/` (log, tamper_evident, install_log — NO matter_audit)

## Componentes NO incluidos (pertenecen a DESPACHO-JURIDICO)

- `albra/matters/` — gestión de expedientes
- `albra/marketplace/` — marketplace de skills + X402 USDC
- `albra/whitelabel/` — multi-tenant white-label
- `albra/scheduling/` — programación de tareas
- `albra/documents/` — redline de documentos
- `albra/review/` — revisión tabular
- `albra/api/` — HTTP API FastAPI
- `albra/cli.py` — CLI
- `albra/audit/matter_audit.py` — auditoría de expedientes
- `data/` — BDs SQLite en vivo
- `CONTEXTO JURIDICO/` — historial del despacho
- `docs/` — docs del despacho

## Instalación

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Tests

```bash
.venv/bin/pytest -q
.venv/bin/ruff check albra/ tests/ src/
```

## Corpus V1.4

10 documentos, 2107 artículos, hashes SHA-256 verificados:

| Documento | Artículos | Hash match |
|---|---:|---|
| Constitución 1991 | 380 | ✓ |
| Ley 1564/2012 (CGP) | 627 | ✓ |
| Ley 640/2001 | 51 | ✓ |
| Ley 906/2004 (CPP) | 564 | ✓ |
| Código Sustantivo del Trabajo | 485 | ✓ |
| Sentencias T-001/002/003/100/445-2020 | texto reconstruido | ✓ |

## Limitaciones heredadas

- B7 permanece **PARCIALMENTE RESUELTA** — sin detección semántica de contradicciones.
- Draft Citation Audit NO verifica fidelidad de paráfrasis (requiere NLI).
- No hay vigencia histórica ni parcial.
- Corpus V1.4 parcial (5 cuerpos legales + 5 sentencias; sin Código Civil, CPACA, etc.).
- RESUELTO (migración de conocimiento): el boot ahora SIEMBRA el corpus canónico (V1.4 + leyes V1.3) en el retrieval provider — ver `docs/CORPUS.md` y `albra/knowledge/corpus_seed.py`.

## Estado de validación

* Extracción original: `DESPACHO-JURIDICO@fe9d80e` (V8.0 Fase 4).
* Migración seed-parity: ADN universal de AGENTE-GENERAL integrado (106/106 componentes, rama `feat/seed-parity`).
* Migración de conocimiento jurídico: el corpus V1.4 (+ leyes V1.3) está **integrado y utilizable** — boot con siembra verificada, retrieval E2E con citas y provenance, cero dependencia funcional del despacho. Ver `docs/CORPUS.md`.
* Suite completa: 1133+ tests pasando; tests de migración en `tests/knowledge/test_corpus_seed.py` e independencia en `tests/test_knowledge_independence.py`.

## Trazabilidad

- **Origen:** `ALBRA8/DESPACHO-JURIDICO` commit `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73`
- **Estado origen:** V8.0 Fase 4 — ACCEPTANCE VERIFIED WITH LIMITATIONS
- **Identidad renombrada:** conforme decisión D1 del plan de extracción
- **MCP server:** ajustado con stubs para `_tenant_is_authorized`, `_matter_store`, `_audit_chain` (los matters/matter_audit viven en DESPACHO-JURIDico)

## Licencia

Propietaria — ALBRA.
