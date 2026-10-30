"""Commands subpackage — one file per CLI command group.

Each module exposes:
    register(subparsers, ctx_factory) -> None

`ctx_factory` is a callable returning a `CLIContext` (built lazily on
first invocation so `--help` doesn't trigger runtime startup).
"""

from albra.cli.commands.agent import register as register_agent
from albra.cli.commands.audit import register as register_audit
from albra.cli.commands.capabilities import register as register_capabilities
from albra.cli.commands.config import register as register_config
from albra.cli.commands.doctor import register as register_doctor
from albra.cli.commands.execution import register as register_execution
from albra.cli.commands.health import register as register_health
from albra.cli.commands.memory import register as register_memory
from albra.cli.commands.providers import register as register_providers
from albra.cli.commands.skills import register as register_skills
from albra.cli.commands.tools import register as register_tools

__all__ = [
    "register_agent",
    "register_audit",
    "register_capabilities",
    "register_config",
    "register_doctor",
    "register_execution",
    "register_health",
    "register_memory",
    "register_providers",
    "register_skills",
    "register_tools",
]
