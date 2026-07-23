import json
import logging
from json import JSONDecodeError

from django.db import DatabaseError
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Document
from .serializers import serialize_document
from .services import create_document, delete_document, update_document
from .validation import DocumentValidationError

DATABASE_ALIAS = "documents"
ALLOWED_ORDERINGS = {
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "filename",
    "-filename",
}
logger = logging.getLogger(__name__)


def _error(
    code: str,
    message: str,
    *,
    status: int,
    fields: dict[str, str] | None = None,
) -> JsonResponse:
    payload: dict[str, object] = {"code": code, "message": message}
    if fields:
        payload["fields"] = fields
    return JsonResponse({"error": payload}, status=status)


def _validation_error(error: DocumentValidationError) -> JsonResponse:
    return _error(
        error.code,
        error.message,
        status=error.status,
        fields=error.fields,
    )


def _persistence_error() -> JsonResponse:
    return _error(
        "document_persistence_failed",
        "The document could not be persisted. Try again.",
        status=500,
    )


def _method_not_allowed(allowed: list[str]) -> JsonResponse:
    response = _error(
        "method_not_allowed",
        "This method is not supported for the requested document resource.",
        status=405,
    )
    response["Allow"] = ", ".join(allowed)
    return response


def _find_document(document_id):
    return Document.objects.using(DATABASE_ALIAS).filter(pk=document_id).first()


def _list_documents(request) -> JsonResponse:
    ordering = request.GET.get("ordering", "-created_at")
    if ordering not in ALLOWED_ORDERINGS:
        return _error(
            "invalid_query",
            "Document query is invalid.",
            status=400,
            fields={"ordering": "Choose a supported ordering value."},
        )

    documents = Document.objects.using(DATABASE_ALIAS).all()
    query = request.GET.get("q", "").strip()
    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(filename__icontains=query))
    content_type = request.GET.get("content_type", "").strip()
    if content_type:
        documents = documents.filter(content_type=content_type)

    items = list(documents.order_by(ordering))
    tag = request.GET.get("tag", "").strip().casefold()
    if tag:
        items = [
            document
            for document in items
            if any(stored_tag.casefold() == tag for stored_tag in document.tags)
        ]
    return JsonResponse({"documents": [serialize_document(document) for document in items]})


def _upload_documents(request) -> JsonResponse:
    uploads = request.FILES.getlist("files")
    if not uploads:
        return _error(
            "missing_files",
            "Choose at least one document to upload.",
            status=400,
            fields={"files": "Choose at least one document."},
        )

    results = []
    failures: list[DocumentValidationError] = []
    for upload in uploads:
        try:
            document = create_document(upload)
        except DocumentValidationError as error:
            failures.append(error)
            results.append(
                {
                    "filename": getattr(upload, "name", "document"),
                    "status": "error",
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "fields": error.fields,
                    },
                }
            )
        except (DatabaseError, OSError):
            logger.exception("Document upload persistence failed.")
            error = DocumentValidationError(
                "document_persistence_failed",
                "The document could not be persisted. Try again.",
                status=500,
            )
            failures.append(error)
            results.append(
                {
                    "filename": getattr(upload, "name", "document"),
                    "status": "error",
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "fields": error.fields,
                    },
                }
            )
        else:
            results.append(
                {
                    "filename": document.filename,
                    "status": "uploaded",
                    "document": serialize_document(document),
                }
            )

    if len(failures) == 1 and len(results) == 1:
        return _validation_error(failures[0])
    return JsonResponse(
        {"results": results},
        status=207 if failures else 201,
    )


@ensure_csrf_cookie
def document_collection(request):
    if request.method == "GET":
        try:
            return _list_documents(request)
        except DatabaseError:
            logger.exception("Document listing failed.")
            return _persistence_error()
    if request.method == "POST":
        return _upload_documents(request)
    return _method_not_allowed(["GET", "POST"])


def _parse_patch(request) -> tuple[dict[str, object], object | None]:
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body)
        except (JSONDecodeError, UnicodeDecodeError):
            raise DocumentValidationError(
                "malformed_json",
                "Request body must be valid JSON.",
            ) from None
        if not isinstance(payload, dict):
            raise DocumentValidationError(
                "invalid_metadata",
                "Document metadata must be a JSON object.",
            )
        return payload, None

    if request.content_type.startswith("multipart/"):
        try:
            parser = MultiPartParser(
                request.META,
                request,
                request.upload_handlers,
                request.encoding,
            )
            form, files = parser.parse()
            metadata = json.loads(form.get("metadata", "{}"))
        except (JSONDecodeError, UnicodeDecodeError, MultiPartParserError):
            raise DocumentValidationError(
                "malformed_request",
                "Multipart metadata must contain valid JSON.",
            ) from None
        if not isinstance(metadata, dict):
            raise DocumentValidationError(
                "invalid_metadata",
                "Document metadata must be a JSON object.",
            )
        return metadata, files.get("file")

    raise DocumentValidationError(
        "unsupported_media_type",
        "Use application/json or multipart/form-data.",
        status=415,
    )


def document_detail(request, document_id):
    if request.method not in {"GET", "PATCH", "DELETE"}:
        return _method_not_allowed(["GET", "PATCH", "DELETE"])

    try:
        document = _find_document(document_id)
    except DatabaseError:
        logger.exception("Document lookup failed for %s.", document_id)
        return _persistence_error()
    if document is None:
        return _error(
            "document_not_found",
            "The requested document does not exist.",
            status=404,
        )

    if request.method == "GET":
        return JsonResponse(serialize_document(document))
    if request.method == "DELETE":
        try:
            delete_document(document)
        except FileNotFoundError:
            return _error(
                "stored_file_missing",
                "The stored file is unavailable.",
                status=404,
            )
        except (DatabaseError, OSError):
            logger.exception("Document deletion failed for %s.", document.id)
            return _persistence_error()
        return HttpResponse(status=204)

    try:
        metadata, replacement = _parse_patch(request)
        document = update_document(document, metadata, replacement)
    except DocumentValidationError as error:
        return _validation_error(error)
    except Document.DoesNotExist:
        return _error(
            "document_not_found",
            "The requested document does not exist.",
            status=404,
        )
    except (DatabaseError, OSError):
        logger.exception("Document update failed for %s.", document.id)
        return _persistence_error()
    return JsonResponse(serialize_document(document))


def document_download(request, document_id):
    if request.method != "GET":
        return _method_not_allowed(["GET"])

    try:
        document = _find_document(document_id)
    except DatabaseError:
        logger.exception("Document lookup failed for %s.", document_id)
        return _persistence_error()
    if document is None:
        return _error(
            "document_not_found",
            "The requested document does not exist.",
            status=404,
        )
    try:
        stored_file_exists = document.file.storage.exists(document.file.name)
    except OSError:
        logger.exception("Document storage lookup failed for %s.", document.id)
        return _persistence_error()
    if not stored_file_exists:
        return _error(
            "stored_file_missing",
            "The stored file is unavailable.",
            status=404,
        )
    try:
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.filename,
            content_type=document.content_type,
        )
    except FileNotFoundError:
        return _error(
            "stored_file_missing",
            "The stored file is unavailable.",
            status=404,
        )
    except OSError:
        logger.exception("Document download failed for %s.", document.id)
        return _persistence_error()
