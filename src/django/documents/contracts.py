import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping
from uuid import UUID


class FailureDisposition(StrEnum):
    RETRIED = "retried"
    DEAD_LETTERED = "dead_lettered"


def safe_error_code(value: str, *, fallback: str = "callback_failed") -> str:
    return value if re.fullmatch(r"[a-z][a-z0-9_]{0,99}", value) else fallback


@dataclass(frozen=True)
class DocumentEventEnvelope:
    event_id: UUID
    event_type: str
    schema_version: int
    document_id: UUID
    content_revision: int
    source_sha256: str
    payload: Mapping[str, object]
    occurred_at: datetime

    def __post_init__(self):
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(self.payload)),
        )


@dataclass(frozen=True)
class ClaimedDocumentEvent:
    envelope: DocumentEventEnvelope
    claim_token: UUID
    attempt_count: int


@dataclass(frozen=True)
class DocumentRevisionSnapshot:
    document_id: UUID
    content_revision: int
    source_sha256: str
    content_type: str
    size: int
    updated_at: datetime
