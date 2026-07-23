from collections.abc import Mapping
from uuid import UUID

from .models import DocumentOutboxEvent

DATABASE_ALIAS = "documents"


def append_document_event(
    *,
    event_type: str,
    document_id: UUID,
    content_revision: int,
    source_sha256: str,
    payload: Mapping[str, object],
) -> DocumentOutboxEvent:
    return DocumentOutboxEvent.objects.using(DATABASE_ALIAS).create(
        event_type=event_type,
        document_id=document_id,
        content_revision=content_revision,
        source_sha256=source_sha256,
        payload=dict(payload),
    )
