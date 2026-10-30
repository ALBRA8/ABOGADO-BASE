# REGISTRO DE DECISIONES — ABOGADO-BASE

Este registro diferencia decisiones explícitas de propuestas e informes. Una decisión solo puede marcarse como aprobada si existe aprobación real.

## D-ABOGADO-BASE-001 — Extracción del agente jurídico de DESPACHO-JURIDICO

- **Identificador:** D-ABOGADO-BASE-001
- **Fecha:** 2026-10-30
- **Estado:** APPROVED
- **Contexto:** El agente jurídico vivía integrado dentro de DESPACHO-JURIDICO (commit `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73`). La misión V9.0 de separación arquitectónica autorizó la extracción a un repositorio independiente ABOGADO-BASE para separar las responsabilidades de agente (abogado) y oficina (despacho).

- **Decisión:** Extraer el agente jurídico y su núcleo compartido a ABOGADO-BASE como proyecto independiente. DESPACHO-JURIDICO NO se modifica durante esta fase.

- **Alcance (Fase 2 únicamente):**
  - Clone del repositorio vacío ABOGADO-BASE.
  - Copia de componentes lawyer-specific + núcleo compartido.
  - Ajuste de identidad (D1 del plan).
  - Creación de README + CONTEXTO documentando origen real.
  - Commit inicial (sin push).

- **Componentes extraídos:**
  - AGENTE-GENERAL (`src/adapters/general_adapter.py`) + arnés (`src/harness/`, `src/bridges/`, `src/bootstrap/`)
  - Chaleco jurídico: `albra/lawyer/`, `albra/knowledge/` (incluido corpus V1.4), `albra/evidence/`, `albra/reasoning/`, `albra/playbooks/`, `albra/research/`, `albra/agents/`, `albra/eval/`
  - Núcleo compartido: `albra/identity/`, `albra/runtime/`, `albra/llm/`, `albra/providers/`, `albra/memory/`, `albra/tools/`, `albra/capabilities/`, `albra/config/`, `albra/observability/`, `albra/doctor/`, `albra/events/`, `albra/handoffs/`, `albra/resilience/`, `albra/mcp/`, `albra/security/`, `albra/comms/`, `albra/multimodal/`, `albra/files/`, `albra/workflows/`, `albra/audit/` (core sin matter_audit)

- **Componentes NO extraídos (pertenecen a DESPACHO-JURIDico):**
  - `albra/matters/`, `albra/marketplace/`, `albra/whitelabel/`, `albra/scheduling/`, `albra/documents/`, `albra/review/`, `albra/api/`, `albra/cli.py`, `albra/audit/matter_audit.py`
  - `data/`, `CONTEXTO JURIDICO/`, `docs/`, `INICIAR_ALBRA.*`, `DESPLEGAR.md`, `scripts/demo.py`

- **Ajuste identidad (D1):**
  - `name`: "DESPACHO JURÍDICO DIGITAL ALBRA" → "ABOGADO BASE ALBRA"
  - `codename`: "ALBRA-BASE-V1" → "ALBRA-ABOGADO-V1"
  - `role`: "AGENTE BASE DEL DESPACHO JURÍDICO ALBRA" → "ABOGADO BASE INDEPENDIENTE ALBRA"

- **Ajuste MCP server:** top-level import `from albra.matters.store import _tenant_is_authorized` reemplazado por stub local fail-closed. Lazy imports de MatterStore/MatterAudit retornan None. El abogado no gestiona matters.

- **Tests excluidos:** 7 tests con dependencias directas de `albra.matters` o `albra.audit.matter_audit` removidos (se conservan en DESPACHO-JURIDico).

- **Consecuencias:**
  - ABOGADO-BASE es un repositorio independiente con commit inicial.
  - El núcleo compartido está duplicado en ambos repos (costo de independencia).
  - DESPACHO-JURIDico permanece intacto — sin modificaciones.
  - Corpus V1.4 hashes SHA-256 conservados íntegramente.
  - No se inventa historial Git ni resultados de pruebas.
  - No se introducen nuevas capacidades jurídicas.

- **Evidencia:** Commit de origen `fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73` (DESPACHO-JURIDico). Commit inicial ABOGADO-BASE (pendiente de registro tras commit local). Push NO realizado (pendiente autorización).

- **Condiciones para revisar:** Fase 3 (verificación independiente) debe ejecutarse antes de declarar ABOGADO-BASE funcional. Fase 4 (limpieza DESPACHO-JURIDico) requiere Fase 3 PASS primero.

## Regla para nuevas entradas

Cada decisión futura debe incluir identificador, fecha, estado, contexto, decisión, alternativas relevantes, consecuencias, evidencia o enlaces, y condiciones para revisarla. Registrar una propuesta como `PROPOSED`; no convertirla en `APPROVED` por repetición.
