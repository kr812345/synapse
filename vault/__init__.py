"""Encrypted credential store for Pip."""

from vault.approvals import ApprovalGate
from vault.store import VaultStore

__all__ = ["ApprovalGate", "VaultStore"]
