"""Client Master enumerations."""
from __future__ import annotations

from enum import Enum


class ClientStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    CLOSED = "closed"
