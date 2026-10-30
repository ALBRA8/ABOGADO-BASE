"""Plugins subpackage.

A plugin contributes tools/skills/providers/interfaces WITHOUT modifying
core. Plugins are registered via the PluginManager; their PluginManifest
declares contributions, dependencies, and a health check endpoint.
"""

from albra.plugins.loader import (
    DiscoveredPlugin,
    LoaderResult,
    PluginLoader,
)
from albra.plugins.manager import (
    PluginAlreadyRegisteredError,
    PluginManager,
    PluginNotFoundError,
    PluginRecord,
    PluginValidationError,
)
from albra.plugins.manifest import PluginManifest
from albra.plugins.validator import (
    PluginValidationResult,
    PluginValidator,
)

__all__ = [
    "DiscoveredPlugin",
    "LoaderResult",
    "PluginLoader",
    "PluginAlreadyRegisteredError",
    "PluginManager",
    "PluginNotFoundError",
    "PluginRecord",
    "PluginValidationError",
    "PluginManifest",
    "PluginValidationResult",
    "PluginValidator",
]
