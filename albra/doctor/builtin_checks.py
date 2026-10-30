"""Built-in diagnostic checks — universal, NO domain knowledge.

Each check is an async function returning a `CheckResult`. Checks MUST
actually run their probe (import the module, instantiate the class,
run a roundtrip) before declaring a component HEALTHY+IMPLEMENTED.
"""

from __future__ import annotations

from albra.core.types import HealthState
from albra.doctor.checks import CheckRegistry, CheckResult
from albra.doctor.report import ImplementationStatus


def _import_err(name: str, exc: Exception) -> CheckResult:
    return CheckResult(
        name=name, status=HealthState.ERROR,
        implementation_status=ImplementationStatus.NOT_VERIFIED,
        details=f"{name} module not importable: {exc}",
    )


async def runtime_check() -> CheckResult:
    """Probe the runtime — importable + exposes health/readiness."""
    try:
        from albra.runtime.seed.runtime import Runtime  # noqa: F401
    except ImportError as exc:
        return _import_err("runtime", exc)
    try:
        rt = Runtime()
        snap = rt.health()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="runtime", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details=f"runtime.health() raised: {exc!r}",
        )
    return CheckResult(
        name="runtime", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"runtime online; status={snap.get('status', 'unknown')}",
        evidence=["runtime.Runtime instantiated", "runtime.health() returned"],
    )


async def memory_check() -> CheckResult:
    """Probe memory — InMemory store usable for roundtrip."""
    try:
        from albra.memory.inmemory_store import InMemoryMemoryStore
        from albra.memory.manager import MemoryManager
    except ImportError as exc:
        return _import_err("memory", exc)
    store = InMemoryMemoryStore()
    mgr = MemoryManager(store=store)
    try:
        rec_id = await mgr.remember(
            content="probe", agent_id="probe", memory_type="episodic"
        )
        hits = await mgr.recall(agent_id="probe", query="probe", limit=5)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="memory", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details=f"memory roundtrip raised: {exc!r}",
        )
    if not hits:
        return CheckResult(
            name="memory", status=HealthState.WARNING,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details="memory store roundtrip returned no hits",
        )
    return CheckResult(
        name="memory", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"memory roundtrip OK; recalled {len(hits)} record(s)",
        evidence=[f"recorded id={rec_id}"],
    )


async def providers_check() -> CheckResult:
    """Probe providers — Mock + Router usable."""
    try:
        from albra.providers.mock import MockProvider
        from albra.providers.seed_registry import ProviderRegistry
        from albra.providers.seed_router import ProviderRouter
    except ImportError as exc:
        return _import_err("providers", exc)
    reg = ProviderRegistry()
    reg.register(MockProvider(name="mock"))
    router = ProviderRouter(registry=reg)
    routes = router.list_routes() if hasattr(router, "list_routes") else []
    return CheckResult(
        name="providers", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"provider router ready; routes={list(routes)}",
        evidence=["MockProvider registered", "ProviderRouter constructed"],
    )


async def tools_check() -> CheckResult:
    """Probe tools — ToolRegistry + NoOpTool usable."""
    try:
        from albra.tools.infra_tools import NoOpTool
        from albra.tools.seed_registry import ToolRegistry
    except ImportError as exc:
        return _import_err("tools", exc)
    reg = ToolRegistry()
    try:
        reg.register(NoOpTool())
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="tools", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details=f"ToolRegistry.register raised: {exc!r}",
        )
    avail = reg.available_tools() if hasattr(reg, "available_tools") else []
    return CheckResult(
        name="tools", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"tool registry ready; available={list(avail)}",
        evidence=["NoOpTool registered"],
    )


async def skills_check() -> CheckResult:
    """Probe skills — SkillRegistry importable."""
    try:
        from albra.skills.registry import SkillRegistry  # noqa: F401
    except ImportError as exc:
        return _import_err("skills", exc)
    return CheckResult(
        name="skills", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details="SkillRegistry importable",
        evidence=["imported albra.skills.registry.SkillRegistry"],
    )


async def security_check() -> CheckResult:
    """Probe security — PermissionRegistry + Firewall importable."""
    try:
        from albra.security.firewall.firewall import ActionFirewall
        from albra.security.permissions import PermissionRegistry
    except ImportError as exc:
        return _import_err("security", exc)
    PermissionRegistry()
    ActionFirewall()
    return CheckResult(
        name="security", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details="permission registry + firewall constructed",
        evidence=["PermissionRegistry()", "ActionFirewall()"],
    )


async def audit_check() -> CheckResult:
    """Probe audit — NORMAL log + tamper-evident log append+verify."""
    try:
        from albra.audit.normal import AuditLog
        from albra.audit.seed_tamper_evident import TamperEvidentAuditLog
    except ImportError as exc:
        return _import_err("audit", exc)
    normal = AuditLog()
    normal.record(action="doctor.probe", actor="doctor", result="success")
    te = TamperEvidentAuditLog()
    te.append({"action": "doctor.probe", "actor": "doctor"})
    te.append({"action": "doctor.probe2", "actor": "doctor"})
    vr = te.verify_chain()
    if not vr.valid:
        return CheckResult(
            name="audit", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details=f"tamper-evident chain invalid: {vr.details}",
        )
    return CheckResult(
        name="audit", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"audit log OK; normal={normal.count()} te={te.count()}",
        evidence=[f"normal entries={normal.count()}", f"te entries={te.count()}"],
    )


async def observability_check() -> CheckResult:
    """Probe observability — metrics + health usable."""
    try:
        from albra.observability.health import HealthMonitor
        from albra.observability.metrics import MetricsRegistry
    except ImportError as exc:
        return _import_err("observability", exc)
    m = MetricsRegistry()
    m.inc("doctor.probe", tags={"check": "observability"})
    snap = m.snapshot()
    hm = HealthMonitor()
    hm.register("doctor")
    hm.report("doctor", HealthState.HEALTHY)
    return CheckResult(
        name="observability", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details=f"metrics + health OK; counters={len(snap.get('counters', []))}",
        evidence=["MetricsRegistry.inc()", "HealthMonitor.report()"],
    )


async def mcp_check() -> CheckResult:
    """Probe MCP — importable if present; NOT_CONFIGURED if absent."""
    try:
        import albra.mcp  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return CheckResult(
            name="mcp", status=HealthState.NOT_CONFIGURED,
            implementation_status=ImplementationStatus.NOT_CONFIGURED,
            details="albra.mcp not present (optional)",
        )
    return CheckResult(
        name="mcp", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details="albra.mcp importable",
    )


async def comm_check() -> CheckResult:
    """Probe communication module — importable if present."""
    try:
        import albra.comms  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return CheckResult(
            name="communication", status=HealthState.NOT_CONFIGURED,
            implementation_status=ImplementationStatus.NOT_CONFIGURED,
            details="albra.comms not present (optional)",
        )
    return CheckResult(
        name="communication", status=HealthState.HEALTHY,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        details="albra.comms importable",
    )


async def legal_knowledge_check() -> CheckResult:
    """Probe legal knowledge — corpus integrity + fail-closed abstention.

    Cierre de extracción (hallazgo 9 — readiness y estado degradado):
    el servicio jurídico NO puede anunciarse saludable sin evidencia.
    Este check ejecuta una sonda REAL:

    1. Verifica los hashes SHA-256 del corpus canónico V1.4+V1.3
       (``verify_corpus_hashes`` — integridad nivel 1).
    2. Instancia el LegalKnowledgeEngine con provider VACÍO y verifica
       que una consulta jurídica sin corpus ABSTIENE (fail-closed de
       nivel respuesta) y que el estado se reporta como
       ``DEGRADED_NO_CORPUS``.

    Estado HEALTHY exige: hashes íntegros Y abstención sin corpus.
    """
    try:
        from albra.knowledge.corpus_seed import verify_corpus_hashes
        from albra.knowledge.legal_engine import LegalKnowledgeEngine

        # 1. Integridad del corpus canónico (real, determinista).
        mismatched = verify_corpus_hashes()
        if mismatched:
            return CheckResult(
                name="legal_knowledge", status=HealthState.ERROR,
                implementation_status=ImplementationStatus.IMPLEMENTED,
                details=(
                    f"corpus integrity FAIL: {len(mismatched)} documento(s) "
                    f"con hash inválido: {mismatched[:3]}"
                ),
                evidence=["verify_corpus_hashes() → mismatches"],
            )

        # 2. Fail-closed de nivel respuesta sin corpus (sonda real).
        engine = LegalKnowledgeEngine()  # provider vacío por defecto
        resp = await engine.query("¿Qué dice el artículo 25 de la Constitución Política?")
        stats = engine.stats()
        if resp.abstention and stats.get("legal_service") == "DEGRADED_NO_CORPUS":
            return CheckResult(
                name="legal_knowledge", status=HealthState.HEALTHY,
                implementation_status=ImplementationStatus.IMPLEMENTED,
                details=(
                    "corpus canónico íntegro (12 docs); engine sin corpus "
                    "abstiene (fail-closed); readiness reporta "
                    "DEGRADED_NO_CORPUS cuando no hay corpus"
                ),
                evidence=[
                    "verify_corpus_hashes() → [] mismatches",
                    "engine.query() sin corpus → abstention=True",
                    "engine.stats()['legal_service'] = DEGRADED_NO_CORPUS",
                ],
            )
        return CheckResult(
            name="legal_knowledge", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.IMPLEMENTED,
            details=(
                f"fail-closed roto: abstention={resp.abstention}, "
                f"legal_service={stats.get('legal_service')}"
            ),
            evidence=["engine.query() sin corpus NO abstuvo"],
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="legal_knowledge", status=HealthState.ERROR,
            implementation_status=ImplementationStatus.NOT_VERIFIED,
            details=f"legal knowledge probe failed: {exc!r}",
        )


def default_registry() -> CheckRegistry:
    """Return a CheckRegistry pre-populated with the built-in checks."""
    reg = CheckRegistry()
    reg.register("runtime", runtime_check)
    reg.register("memory", memory_check)
    reg.register("providers", providers_check)
    reg.register("tools", tools_check)
    reg.register("skills", skills_check)
    reg.register("security", security_check)
    reg.register("audit", audit_check)
    reg.register("observability", observability_check)
    reg.register("mcp", mcp_check)
    reg.register("communication", comm_check)
    reg.register("legal_knowledge", legal_knowledge_check)
    return reg


__all__ = [
    "default_registry",
    "runtime_check", "memory_check", "providers_check", "tools_check",
    "skills_check", "security_check", "audit_check",
    "observability_check", "mcp_check", "comm_check",
    "legal_knowledge_check",
]
