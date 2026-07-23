from uuid import uuid4

from django.db import models


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    file = models.FileField(max_length=255)
    filename = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    content_type = models.CharField(max_length=127)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    content_revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentOutboxEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "document.created"
        CONTENT_REPLACED = "document.content_replaced"
        METADATA_UPDATED = "document.metadata_updated"
        DELETED = "document.deleted"

    class Status(models.TextChoices):
        PENDING = "pending"
        CLAIMED = "claimed"
        DISPATCHED = "dispatched"
        DEAD_LETTER = "dead_letter"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_type = models.CharField(max_length=64, choices=EventType.choices)
    schema_version = models.PositiveIntegerField(default=1)
    document_id = models.UUIDField()
    content_revision = models.PositiveIntegerField()
    source_sha256 = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    available_at = models.DateTimeField(auto_now_add=True)
    claim_token = models.UUIDField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error_code = models.CharField(max_length=100, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="doc_outbox_due_idx",
            ),
            models.Index(
                fields=["status", "claim_expires_at"],
                name="doc_outbox_lease_idx",
            ),
            models.Index(
                fields=["document_id", "content_revision"],
                name="doc_outbox_revision_idx",
            ),
            models.Index(fields=["occurred_at"], name="doc_outbox_time_idx"),
        ]
