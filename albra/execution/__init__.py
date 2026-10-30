"""Execution subpackage — runner, traces, idempotency, replay.

Public API:
    ExecutionRunner   — orchestrates a single execution
    ExecutionTrace    — detailed per-execution trace
    TraceStep         — a single phase entry on a trace
    IdempotencyManager — detects duplicate execution keys (safe retries)
    TraceReplay       — replays an execution from its trace
"""

from albra.execution.idempotency import IdempotencyManager, IdempotencyRecord
from albra.execution.replay import ReplayHandler, ReplayResult, TraceReplay
from albra.execution.runner import CANONICAL_PHASES, ExecutionRunner, PhaseHandler
from albra.execution.step import TraceStep
from albra.execution.trace import ExecutionTrace

__all__ = [
    "ExecutionRunner",
    "ExecutionTrace",
    "TraceStep",
    "IdempotencyManager",
    "IdempotencyRecord",
    "TraceReplay",
    "ReplayResult",
    "ReplayHandler",
    "CANONICAL_PHASES",
    "PhaseHandler",
]
