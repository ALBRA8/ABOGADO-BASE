"""
ABOGADO BASE ALBRA - V1.0
Agente jurídico independiente.

Origen: extraído de DESPACHO-JURIDICO commit fe9d80e4cc6b6be37af0f1208ad7421d7c7fde73
como parte de la misión de separación arquitectónica V9.0.

Identidad del organismo.
"""
from albra.identity.agent import Agent
from albra.identity.manifest import AGENT_MANIFEST, AgentIdentity

__all__ = ["AGENT_MANIFEST", "Agent", "AgentIdentity"]

__version__ = "1.0.0"
