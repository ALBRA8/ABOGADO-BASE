"""Firewall subpackage — DEFAULT-DENY action gate.

CRITICAL INVARIANTS enforced here:
  * Every external action MUST pass through `ActionFirewall.evaluate`.
  * DEFAULT-DENY: no matching rule → DENY.
  * KillSwitch is GLOBAL and blocks ALL external actions when active.
  * Cooldowns + rate limits are enforced BEFORE rule evaluation.
  * Kill switch activation/deactivation is audit-logged.
"""

from albra.security.firewall.cooldown import CooldownManager, CooldownRecord
from albra.security.firewall.firewall import ActionFirewall, FirewallVerdict
from albra.security.firewall.kill_switch import KillSwitch, KillSwitchState
from albra.security.firewall.rate_limit import RateLimiter
from albra.security.firewall.rules import FirewallRule

__all__ = [
    "ActionFirewall",
    "FirewallVerdict",
    "FirewallRule",
    "KillSwitch",
    "KillSwitchState",
    "CooldownManager",
    "CooldownRecord",
    "RateLimiter",
]
