"""Handoffs ALBRA - protocolo para futura delegación entre agentes."""
from albra.handoffs.protocol import HandoffEnvelope, HandoffProtocol

__all__ = []


# -------------------------------------------------------
# Seed parity additions (AGENTE-GENERAL → ABOGADO-BASE)
# -------------------------------------------------------
from albra.handoffs.contract import (
    HandoffRequest,
    HandoffResponse,
    HandoffStatus,
)
from albra.handoffs.evidence import (
    HandoffEvidence,
    HandoffEvidenceChain,
    build_evidence,
)
from albra.handoffs.manager import AuditSink, HandoffManager
from albra.handoffs.registry import (
    AgentRecord,
    AgentRegistry,
    HandoffHandler,
)
from albra.handoffs.timeout import (
    HandoffTimeout,
    TimeoutAuditRecord,
    TimeoutAuditSink,
)

__all__ += [
    # contract
    "HandoffRequest",
    "HandoffResponse",
    "HandoffStatus",
    # registry
    "AgentRegistry",
    "AgentRecord",
    "HandoffHandler",
    # manager
    "HandoffManager",
    "AuditSink",
    # evidence
    "HandoffEvidence",
    "HandoffEvidenceChain",
    "build_evidence",
    # timeout
    "HandoffTimeout",
    "TimeoutAuditRecord",
    "TimeoutAuditSink",
]
