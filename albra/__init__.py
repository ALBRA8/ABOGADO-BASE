"""
ABOGADO BASE ALBRA - V1.0
Agente jurídico independiente, construido sobre el ADN universal ALBRA.

Origen: extraído de DESPACHO-JURIDICO commit fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73
como parte de la misión de separación arquitectónica V9.0.

Identidad del organismo.

Superficie pública (seed parity): igual que ALBRA AGENT SEED V1.0.
    from albra import Agent, Runtime, SeedConfig, Message, Tool, MemoryStore

La especialización jurídica vive en albra.identity (AGENT_MANIFEST,
AgentIdentity/Agent del abogado, importables desde albra.identity).
"""

from albra.core.base import (
    Capability,
    Guardrail,
    LLMProvider,
    MemoryStore,
    Plugin,
    Skill,
    Tool,
    Workflow,
)
from albra.core.config import AgentConfig, SeedConfig
from albra.core.identity import AgentIdentity, AgentManifest

# ------------------------------------------------------------------
# Seed parity additions — espejo exacto de la superficie pública de
# albra_seed (imports mapeados a albra.*). Ver docs/SEED_BASE_README.md
# ------------------------------------------------------------------
from albra.core.types import (
    AgentResponse,
    ApprovalStatus,
    AutonomyLevel,
    CommunicationChannel,
    ComponentStatus,
    Evidence,
    EvidenceType,
    ExecutionStatus,
    HealthState,
    KnowledgeType,
    MemoryType,
    Message,
    ModalityType,
    PolicyDecision,
    Provenance,
    RiskLevel,
    Role,
    RunContext,
    Session,
    Severity,
    ToolCall,
    ToolResult,
)
from albra.feedback import (
    FeedbackManager,
    FeedbackRecord,
    FeedbackStore,
    FeedbackType,
)
from albra.identity.agent import Agent as _LawyerAgent  # noqa: F401 (especialización jurídica)
from albra.identity.manifest import AGENT_MANIFEST
from albra.identity.manifest import AgentIdentity as _LawyerAgentIdentity
from albra.learning import (
    LearningManager,
    LearningProposal,
    LearningSignal,
    LearningStore,
    ProposalGenerator,
    ProposalStatus,
)
from albra.memory import (
    DecisionMemory,
    DecisionRecord,
    MemoryRetriever,
    RetrievalConfig,
    RetrievedMemory,
)
from albra.runtime.seed.agent import Agent
from albra.runtime.seed.runtime import Runtime
from albra.skills import (
    ImprovementProposal,
    SkillEvolutionError,
    SkillEvolutionManager,
    SkillMetrics,
)


def __getattr__(name: str):  # pragma: no cover - lazy public API
    """Lazy-access optional exports so the package stays CORE_ONLY safe.

    `create_app` requires fastapi; `main` requires only stdlib (argparse).
    A2A exports are lazy so importing `albra` in CORE_ONLY mode does not
    pull in the A2A subpackage.
    """
    _A2A_EXPORTS = {
        "AgentCard",
        "A2ACardSkill",
        "manifest_to_card",
        "TaskState",
        "A2AMessage",
        "A2AArtifact",
        "A2ATask",
        "A2ATaskStatus",
        "A2AAdapter",
        "A2ASecurityFilter",
        "A2ASecurityDecision",
        "A2ATransport",
        "InProcessTransport",
        "HTTPTransport",
        "A2AServer",
        "A2AClient",
        "A2ARegistry",
        "A2AAgentRecord",
        "agent_card_to_wire",
        "wire_to_agent_card",
        "message_to_wire",
        "wire_to_message",
        "artifact_to_wire",
        "wire_to_artifact",
        "task_to_wire",
        "wire_to_task",
        "make_jsonrpc_request",
        "make_jsonrpc_response",
        "build_a2a_server",
    }
    if name in _A2A_EXPORTS:
        from albra import a2a as _a2a

        return getattr(_a2a, name)
    if name == "create_app":
        from albra.api.app import create_app
        return create_app
    if name == "main":
        from albra.cli.cli import main
        return main
    if name == "ConfigManager":
        from albra.config import ConfigManager
        return ConfigManager
    raise AttributeError(f"module 'albra' has no attribute {name!r}")


__version__ = "1.0.0"
__seed_version__ = "ALBRA_SEED_V1.0"
__runtime_version__ = "1.0.0"

__all__ = [
    # Identidad del abogado (especialización)
    "AGENT_MANIFEST",
    # Seed parity (ADN universal)
    "Agent",
    "Runtime",
    "AgentIdentity",
    "AgentManifest",
    "SeedConfig",
    "AgentConfig",
    "Message",
    "Role",
    "ToolCall",
    "ToolResult",
    "AgentResponse",
    "Session",
    "Severity",
    "RiskLevel",
    "AutonomyLevel",
    "ExecutionStatus",
    "EvidenceType",
    "MemoryType",
    "KnowledgeType",
    "ComponentStatus",
    "PolicyDecision",
    "Evidence",
    "Provenance",
    "RunContext",
    "ApprovalStatus",
    "HealthState",
    "CommunicationChannel",
    "ModalityType",
    "Tool",
    "MemoryStore",
    "LLMProvider",
    "Guardrail",
    "Skill",
    "Workflow",
    "Plugin",
    "Capability",
    "DecisionRecord",
    "DecisionMemory",
    "MemoryRetriever",
    "RetrievalConfig",
    "RetrievedMemory",
    "FeedbackManager",
    "FeedbackRecord",
    "FeedbackStore",
    "FeedbackType",
    "LearningManager",
    "LearningProposal",
    "LearningSignal",
    "LearningStore",
    "ProposalGenerator",
    "ProposalStatus",
    "SkillMetrics",
    "ImprovementProposal",
    "SkillEvolutionManager",
    "SkillEvolutionError",
    # Lazy exports (resolved on first access via __getattr__):
    "create_app",
    "main",
    "ConfigManager",
]
