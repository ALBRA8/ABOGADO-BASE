# ABOGADO-BASE — ESTADO ACTUAL

- **Estado del documento:** `V1.0 — EXTRACCIÓN INICIAL DE DESPACHO-JURIDICO`
- **Última revisión documental:** 2026-10-30
- **Repositorio:** `ALBRA8/ABOGADO-BASE`
- **Commit de origen:** `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73` (DESPACHO-JURIDICO)
- **Commit inicial ABOGADO-BASE:** pendiente de registro tras commit
- **Push:** NO realizado (pendiente de autorización)

## Resumen ejecutivo V1.0

ABOGADO-BASE V1.0 es el agente jurídico independiente extraído de
DESPACHO-JURIDICO commit `fe9d80e` como parte de la misión de
separación arquitectónica V9.0.

El agente jurídico que vivía dentro del despacho ahora tiene su
propio repositorio, su propia identidad, y puede evolucionar de
manera independiente. DESPACHO-JURIDICO conserva su función como
oficina jurídica.

## Identidad

| Campo | Valor |
|---|---|
| Name | `ABOGADO BASE ALBRA` |
| Codename | `ALBRA-ABOGADO-V1` |
| Versión | `1.0.0` |
| Rol | `ABOGADO BASE INDEPENDIENTE ALBRA` |
| Jurisdicción | `CO` (Colombia) |
| Especialización | `generalista-base` |
| Órganos | 30 (ALBRA_DNA_ORGANS) |
| Principios | 8 (ALBRA_PRINCIPLES) |

## Componentes extraídos

### Núcleo del abogado
- AGENTE-GENERAL — `src/adapters/general_adapter.py`
- Arnés — `src/harness/`, `src/bridges/`, `src/bootstrap/`
- Chaleco jurídico — `albra/lawyer/`, `albra/knowledge/`, `albra/evidence/`, `albra/reasoning/`, `albra/playbooks/`, `albra/research/`, `albra/agents/`, `albra/eval/`
- Corpus V1.4 — `albra/knowledge/colombia/corpus_pilot/` (10 docs, 2107 arts)

### Núcleo compartido
- `albra/identity/`, `albra/runtime/`, `albra/llm/`, `albra/providers/`, `albra/memory/`, `albra/tools/`, `albra/capabilities/`, `albra/config/`, `albra/observability/`, `albra/doctor/`, `albra/events/`, `albra/handoffs/`, `albra/resilience/`, `albra/mcp/`, `albra/security/`, `albra/comms/`, `albra/multimodal/`, `albra/files/`, `albra/workflows/`, `albra/audit/` (core: log, tamper_evident, install_log)

## Ajustes realizados durante la extracción

1. **Identidad renombrada** (decisión D1):
   - `name`: "DESPACHO JURÍDICO DIGITAL ALBRA" → "ABOGADO BASE ALBRA"
   - `codename`: "ALBRA-BASE-V1" → "ALBRA-ABOGADO-V1"
   - `role`: "AGENTE BASE DEL DESPACHO JURÍDICO ALBRA" → "ABOGADO BASE INDEPENDIENTE ALBRA"

2. **MCP server ajustado** (`albra/mcp/server.py`):
   - Top-level import `from albra.matters.store import _tenant_is_authorized` → stub local que retorna False (fail-closed: el abogado no gestiona autorización multi-tenant de matters)
   - `_matter_store()` lazy import → retorna None (el abogado no gestiona matters)
   - `_audit_chain()` lazy import → retorna None (matter_audit vive en DESPACHO-JURIDico)

3. **pyproject.toml renombrado**: `name="albra-despacho-juridico"` → `name="abogado-base"`, `version="2.5.1"` → `version="1.0.0"`

4. **albra/__init__.py** docstring actualizado documentando origen.

## Componentes NO incluidos (pertenecen a DESPACHO-JURIDICO)

- `albra/matters/` — gestión de expedientes
- `albra/marketplace/` — marketplace + X402 USDC
- `albra/whitelabel/` — multi-tenant
- `albra/scheduling/` — scheduler
- `albra/documents/` — redline
- `albra/review/` — tabular review
- `albra/api/` — FastAPI app
- `albra/cli.py` — CLI
- `albra/audit/matter_audit.py` — matter audit
- `data/` — BDs SQLite en vivo
- `CONTEXTO JURIDICO/` — historial del despacho (8 docs)
- `docs/` — docs técnicos del despacho (11 docs)
- `INICIAR_ALBRA.*`, `DESPLEGAR.md` — scripts del despacho
- `scripts/demo.py` — demo del despacho (se conserva `scripts/ingest_pilot.py` y `scripts/v14_ingest/` que son del abogado)

## Tests excluidos (dependencias de oficina)

7 tests removidos porque importan directamente de `albra.matters` o `albra.audit.matter_audit`:
- `tests/mcp/test_server.py`
- `tests/mcp/test_v4_critical_fixes.py`
- `tests/mcp/test_http_server.py`
- `tests/security/test_approval_chain.py`
- `tests/identity/oidc/test_v601_security_corrections.py`
- `tests/identity/oidc/test_tenant_isolation.py`
- `tests/identity/oidc/test_mcp_http_oidc.py`

Estos tests se conservan en DESPACHO-JURIDico donde sus dependencias están disponibles.

## Corpus V1.4 — integridad

10 documentos, 2107 artículos. Hashes SHA-256 verificados coincidentes con `reconstructed_text_hash` declarado en cada doc. Sin alteraciones al corpus durante la extracción.

## Limitaciones heredadas

Heredadas de DESPACHO-JURIDico@fe9d80e (V8.0 Fase 4 — ACCEPTANCE VERIFIED WITH LIMITATIONS):

- B7 permanece **PARCIALMENTE RESUELTA** — sin detección semántica de contradicciones.
- Draft Citation Audit NO verifica fidelidad de paráfrasis (requiere NLI).
- Draft Citation Audit NO verifica aplicabilidad jurídica.
- VigencyChecker false positives residuales posibles (87 → 86 modified tras Fase 4 fix).
- Sin vigencia histórica ni parcial.
- Corpus V1.4 parcial (5 cuerpos legales + 5 sentencias).
- `InMemoryRetrievalProvider` arranca vacío (V1.0 LegalKnowledgeEngine wired pero sin seeding).
- Stale text fix cubre solo `exam.py` (no `citation_audit.py` docstring).

## Estado de validación

- **NO se ha ejecutado Fase 3 (verificación independiente)** — pendiente de autorización.
- **NO se ha ejecutado Fase 4 (limpieza de DESPACHO-JURIDico)** — pendiente de autorización.
- **NO se ha ejecutado Fase 5 (pruebas de separación)** — pendiente de autorización.
- **NO se ha ejecutado Fase 6 (cierre documental)** — pendiente de autorización.

Las capacidades y tests son los que existían en el commit de origen. La verificación independiente determinará si ABOGADO-BASE funciona sin depender de DESPACHO-JURIDico.

## Próximos pasos (NO autorizados todavía)

- Fase 3: verificación integral y aceptación de ABOGADO-BASE.
- Fase 4: limpieza de DESPACHO-JURIDico.
- Fase 5: pruebas finales de separación.
- Fase 6: cierre documental.

Estas fases requieren autorización expresa antes de ejecutarse.
