"""Action Firewall - exports."""
from albra.security.firewall.engine import ActionFirewall
from albra.security.firewall.policy import FIREWALL_POLICIES, FirewallPolicy

__all__ = ["FIREWALL_POLICIES", "ActionFirewall", "FirewallPolicy"]


# -------------------------------------------------------
# Seed parity additions (AGENTE-GENERAL → ABOGADO-BASE)
# -------------------------------------------------------
from albra.security.firewall.cooldown import CooldownManager, CooldownRecord
from albra.security.firewall.firewall import (  # noqa: F811  # parity: la clase canónica del paquete es la del SEED
    ActionFirewall,
    FirewallVerdict,
)
from albra.security.firewall.kill_switch import KillSwitch, KillSwitchState
from albra.security.firewall.rate_limit import RateLimiter
from albra.security.firewall.rules import FirewallRule

__all__ += [
    "ActionFirewall",
    "FirewallVerdict",
    "FirewallRule",
    "KillSwitch",
    "KillSwitchState",
    "CooldownManager",
    "CooldownRecord",
    "RateLimiter",
]
