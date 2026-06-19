"""Client repository PORT (abstract)."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.client.entities import Client


class ClientRepository(ABC):
    @abstractmethod
    def add(self, client: Client) -> None: ...

    @abstractmethod
    def get(self, client_id: uuid.UUID) -> Client | None: ...

    @abstractmethod
    def get_by_pan(self, pan: str) -> Client | None: ...

    @abstractmethod
    def get_by_onboarding_application_id(
        self, application_id: uuid.UUID
    ) -> Client | None: ...

    @abstractmethod
    def list(self, *, limit: int = 50, offset: int = 0) -> list[Client]: ...
