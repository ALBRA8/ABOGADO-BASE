"""Skills subpackage.

A `Skill` is a formal description of a procedure. Specialization layers
register skills; the SEED ships NONE. Skills are installed AFTER seed
initialization without modifying core.
"""

from albra.skills.contract import SkillContract
from albra.skills.evolution import (
    ImprovementProposal,
    SkillEvolutionError,
    SkillEvolutionManager,
    SkillMetrics,
)
from albra.skills.executor import (
    SkillExecutionTrace,
    SkillExecutor,
    SkillHandler,
    SkillNotActiveError,
    SkillPermissionDeniedError,
    SkillTimeoutError,
    SkillValidationError,
)
from albra.skills.lifecycle import (
    InvalidTransitionError,
    LifecycleEvent,
    SkillLifecycle,
    SkillState,
)
from albra.skills.registry import (
    SkillAlreadyRegisteredError,
    SkillNotFoundError,
    SkillRecord,
    SkillRegistry,
)
from albra.skills.validator import SkillValidationResult, SkillValidator

__all__ = [
    "SkillContract",
    "SkillExecutionTrace",
    "SkillExecutor",
    "SkillHandler",
    "SkillNotActiveError",
    "SkillPermissionDeniedError",
    "SkillTimeoutError",
    "SkillValidationError",
    "InvalidTransitionError",
    "LifecycleEvent",
    "SkillLifecycle",
    "SkillState",
    "SkillAlreadyRegisteredError",
    "SkillNotFoundError",
    "SkillRecord",
    "SkillRegistry",
    "SkillValidationResult",
    "SkillValidator",
    "ImprovementProposal",
    "SkillEvolutionError",
    "SkillEvolutionManager",
    "SkillMetrics",
]
