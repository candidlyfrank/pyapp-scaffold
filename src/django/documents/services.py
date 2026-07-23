import logging
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction

from .models import Document, DocumentOutboxEvent
from .outbox import append_document_event
from .validation import DocumentValidationError, normalize_tags, safe_filename, validate_upload

DATABASE_ALIAS = "documents"
MAX_DESCRIPTION_LENGTH = 5_000
logger = logging.getLogger(__name__)


def _validated_metadata(
    metadata: dict[str, object],
    *,
    current: Document | None = None,
) -> dict[str, object]:
    allowed = {"filename", "title", "description", "tags"}
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise DocumentValidationError(
            "invalid_metadata",
            "Document metadata is invalid.",
            fields={name: "This field is not editable." for name in unknown},
        )

    values: dict[str, object] = {}
    if "filename" in metadata:
        values["filename"] = safe_filename(metadata["filename"])
    if "title" in metadata:
        title = metadata["title"]
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 255:
            raise DocumentValidationError(
                "invalid_metadata",
                "Document metadata is invalid.",
                fields={"title": "Enter a title from 1 to 255 characters."},
            )
        values["title"] = title.strip()
    if "description" in metadata:
        description = metadata["description"]
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
            raise DocumentValidationError(
                "invalid_metadata",
                "Document metadata is invalid.",
                fields={
                    "description": (
                        f"Enter a description of {MAX_DESCRIPTION_LENGTH} characters or fewer."
                    )
                },
            )
        values["description"] = description
    if "tags" in metadata:
        values["tags"] = normalize_tags(metadata["tags"])

    if current is None:
        return values
    return {
        "filename": values.get("filename", current.filename),
        "title": values.get("title", current.title),
        "description": values.get("description", current.description),
        "tags": values.get("tags", current.tags),
    }


def create_document(uploaded_file, *, title: str | None = None) -> Document:
    validated = validate_upload(uploaded_file)
    initial_title = title if title is not None else Path(validated.filename).stem
    metadata = _validated_metadata(
        {
            "filename": validated.filename,
            "title": initial_title,
            "description": "",
            "tags": [],
        }
    )
    document = Document(
        **metadata,
        content_type=validated.content_type,
        size=validated.size,
        sha256=validated.sha256,
    )
    document.file.save(uuid4().hex, ContentFile(validated.content), save=False)
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            document.save(using=DATABASE_ALIAS)
            append_document_event(
                event_type=DocumentOutboxEvent.EventType.CREATED,
                document_id=document.id,
                content_revision=document.content_revision,
                source_sha256=document.sha256,
                payload={
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "size": document.size,
                },
            )
    except Exception:
        document.file.storage.delete(document.file.name)
        raise
    return document


def update_document(
    document: Document,
    metadata: dict[str, object],
    replacement=None,
) -> Document:
    validated_file = validate_upload(replacement) if replacement is not None else None
    values = _validated_metadata(metadata)
    old_name: str | None = None
    new_name: str | None = None

    if validated_file is not None:
        new_name = document.file.storage.save(uuid4().hex, ContentFile(validated_file.content))

    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            current = (
                Document.objects.using(DATABASE_ALIAS)
                .select_for_update()
                .get(pk=document.pk)
            )
            old_name = current.file.name
            changed_fields = sorted(
                field for field, value in values.items() if getattr(current, field) != value
            )
            for field in changed_fields:
                setattr(current, field, values[field])
            if validated_file is not None and new_name is not None:
                current.file.name = new_name
                current.content_type = validated_file.content_type
                current.size = validated_file.size
                current.sha256 = validated_file.sha256
                current.content_revision += 1

            if changed_fields or validated_file is not None:
                current.save(using=DATABASE_ALIAS)

            if validated_file is not None:
                append_document_event(
                    event_type=DocumentOutboxEvent.EventType.CONTENT_REPLACED,
                    document_id=current.id,
                    content_revision=current.content_revision,
                    source_sha256=current.sha256,
                    payload={
                        "filename": current.filename,
                        "content_type": current.content_type,
                        "size": current.size,
                    },
                )
            if changed_fields:
                append_document_event(
                    event_type=DocumentOutboxEvent.EventType.METADATA_UPDATED,
                    document_id=current.id,
                    content_revision=current.content_revision,
                    source_sha256=current.sha256,
                    payload={"changed_fields": changed_fields},
                )
    except Exception:
        if new_name is not None:
            document.file.storage.delete(new_name)
        raise

    if new_name is not None and old_name != new_name:
        try:
            document.file.storage.delete(old_name)
        except OSError:
            logger.error(
                "Could not remove the superseded file for document %s.",
                document.pk,
            )
    return current


def delete_document(document: Document) -> None:
    storage = None
    storage_name = ""
    content = b""
    file_removed = False
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            current = (
                Document.objects.using(DATABASE_ALIAS)
                .select_for_update()
                .get(pk=document.pk)
            )
            storage = current.file.storage
            storage_name = current.file.name
            with storage.open(storage_name, "rb") as stored:
                content = stored.read()

            storage.delete(storage_name)
            file_removed = True
            append_document_event(
                event_type=DocumentOutboxEvent.EventType.DELETED,
                document_id=current.id,
                content_revision=current.content_revision,
                source_sha256=current.sha256,
                payload={
                    "filename": current.filename,
                    "content_type": current.content_type,
                },
            )
            current.delete(using=DATABASE_ALIAS)
    except Exception:
        if storage is not None and file_removed and not storage.exists(storage_name):
            storage.save(storage_name, ContentFile(content))
        raise
