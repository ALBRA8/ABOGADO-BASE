"""Runtime subpackage — lifecycle, agent loop, runtime container.

Public API:
    from albra.runtime.seed import (
        Runtime, Agent, AgentState, LifecyclePhase,
        LifecycleEvent, LifecycleManager, AgentLoop, PhaseEvent, PhaseStatus,
    )
"""

from albra.runtime.seed.agent import Agent
from albra.runtime.seed.lifecycle import (
    LifecycleError,
    LifecycleEvent,
    LifecycleListener,
    LifecycleManager,
    LifecyclePhase,
)
from albra.runtime.seed.loop import (
    CANONICAL_PHASES,
    AgentLoop,
    EventHook,
    PhaseEvent,
    PhaseFn,
    PhaseStatus,
)
from albra.runtime.seed.runtime import (
    COMPONENT_APPROVAL_ENGINE,
    COMPONENT_AUDIT_LOGGER,
    COMPONENT_EVIDENCE_COLLECTOR,
    COMPONENT_FIREWALL,
    COMPONENT_MEMORY_MANAGER,
    COMPONENT_MEMORY_STORE,
    COMPONENT_POLICY_ENGINE,
    COMPONENT_PROVIDER_ROUTER,
    COMPONENT_TOOL_REGISTRY,
    REQUIRED_FOR_READINESS,
    Runtime,
)
from albra.runtime.seed.state import AgentState

__all__ = [
    "Runtime",
    "Agent",
    "AgentState",
    "LifecyclePhase",
    "LifecycleEvent",
    "LifecycleManager",
    "LifecycleError",
    "LifecycleListener",
    "AgentLoop",
    "PhaseEvent",
    "PhaseStatus",
    "PhaseFn",
    "EventHook",
    "CANONICAL_PHASES",
    "COMPONENT_FIREWALL",
    "COMPONENT_POLICY_ENGINE",
    "COMPONENT_APPROVAL_ENGINE",
    "COMPONENT_PROVIDER_ROUTER",
    "COMPONENT_TOOL_REGISTRY",
    "COMPONENT_MEMORY_STORE",
    "COMPONENT_MEMORY_MANAGER",
    "COMPONENT_EVIDENCE_COLLECTOR",
    "COMPONENT_AUDIT_LOGGER",
    "REQUIRED_FOR_READINESS",
]
