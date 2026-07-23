from django.urls import reverse


def serialize_document(document) -> dict[str, object]:
    return {
        "id": str(document.id),
        "filename": document.filename,
        "title": document.title,
        "description": document.description,
        "tags": document.tags,
        "contentType": document.content_type,
        "size": document.size,
        "sha256": document.sha256,
        "createdAt": document.created_at.isoformat(),
        "updatedAt": document.updated_at.isoformat(),
        "downloadUrl": reverse("documents:download", args=[document.id]),
    }
