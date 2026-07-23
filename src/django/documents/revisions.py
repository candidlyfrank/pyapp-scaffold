from .contracts import DocumentRevisionSnapshot
from .models import Document

DATABASE_ALIAS = "documents"


def list_document_revisions() -> list[DocumentRevisionSnapshot]:
    documents = (
        Document.objects.using(DATABASE_ALIAS)
        .only(
            "id",
            "content_revision",
            "sha256",
            "content_type",
            "size",
            "updated_at",
        )
        .order_by("id")
    )
    return [
        DocumentRevisionSnapshot(
            document_id=document.id,
            content_revision=document.content_revision,
            source_sha256=document.sha256,
            content_type=document.content_type,
            size=document.size,
            updated_at=document.updated_at,
        )
        for document in documents
    ]
