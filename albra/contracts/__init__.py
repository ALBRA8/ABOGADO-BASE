"""Contracts subpackage — structured output contracts.

Public API:
    from albra.contracts import Contract, ContractRegistry
"""

from __future__ import annotations

from albra.contracts.base import Contract
from albra.contracts.registry import ContractRegistry

__all__ = ["Contract", "ContractRegistry"]
