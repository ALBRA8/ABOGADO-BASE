"""Universal Feedback subpackage.

Public API:
    from albra.feedback import (
        FeedbackManager,
        FeedbackStore,
        InMemoryFeedbackStore,
        SQLiteFeedbackStore,
        FeedbackRecord,
        FeedbackType,
    )

The feedback abstraction is the SEED's universal outcome-evaluation
mechanism. It is a sibling of `evidence` and `audit`:
  * evidence = "what we know"  (facts)
  * audit     = "what happened" (events)
  * feedback  = "how good the outcome was" (evaluation)

The three are complementary; feedback records may reference evidence_ids
and audit entries, but never replace them. The ID prefixes are distinct
(`fb_`, `ev_`, `aud_`) so the three stores can never be confused.
"""

from albra.feedback.manager import FeedbackManager
from albra.feedback.store import (
    FeedbackStore,
    InMemoryFeedbackStore,
    SQLiteFeedbackStore,
)
from albra.feedback.types import FeedbackRecord, FeedbackType

__all__ = [
    "FeedbackManager",
    "FeedbackStore",
    "InMemoryFeedbackStore",
    "SQLiteFeedbackStore",
    "FeedbackRecord",
    "FeedbackType",
]
