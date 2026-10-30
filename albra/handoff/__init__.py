"""Handoff subpackage — agent-to-agent handoff contract + manager.

The SEED ships a fully working in-process handoff pipeline:
  * `HandoffRequest` / `HandoffResponse` carry the formal contract;
  * `AgentRegistry` resolves `target` -> handler;
  * `HandoffManager` initiates + receives handoffs, enforcing deadlines;
  * `HandoffTimeout` fires `status=TIMEOUT` + audit on deadline expiry;
  * `HandoffEvidenceChain` keeps tamper-evident records of every handoff.

NO domain knowledge — purely generic coordination between two ALBRA agents.
"""

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

__all__ = [
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
