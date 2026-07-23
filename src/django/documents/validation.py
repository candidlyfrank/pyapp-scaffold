import csv
import hashlib
import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from django.conf import settings

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MAX_TAGS = 20
MAX_TAG_LENGTH = 50


class DocumentValidationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        fields: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str
    size: int
    sha256: str
    content: bytes


@dataclass(frozen=True)
class FileType:
    content_type: str
    validate: Callable[[bytes], bool]


def _is_utf8(content: bytes) -> bool:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _is_csv(content: bytes) -> bool:
    try:
        text = content.decode("utf-8")
        has_rows = False
        for _row in csv.reader(io.StringIO(text), strict=True):
            has_rows = True
    except (UnicodeDecodeError, csv.Error):
        return False
    return has_rows


def _is_docx(content: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return "word/document.xml" in archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


FILE_TYPES = {
    ".pdf": FileType("application/pdf", lambda content: content.startswith(b"%PDF-")),
    ".docx": FileType(DOCX_CONTENT_TYPE, _is_docx),
    ".txt": FileType("text/plain", _is_utf8),
    ".md": FileType("text/markdown", _is_utf8),
    ".markdown": FileType("text/markdown", _is_utf8),
    ".csv": FileType("text/csv", _is_csv),
}


def safe_filename(value: object) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise DocumentValidationError(
            "invalid_filename",
            "Filename must be a safe, non-empty name.",
            fields={"filename": "Enter a valid filename."},
        )
    filename = PurePosixPath(value.replace("\\", "/")).name.strip()
    if not filename or filename in {".", ".."} or len(filename) > 255:
        raise DocumentValidationError(
            "invalid_filename",
            "Filename must be a safe, non-empty name.",
            fields={"filename": "Enter a valid filename of 255 characters or fewer."},
        )
    return filename


def normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(tag, str) for tag in value):
        raise DocumentValidationError(
            "invalid_metadata",
            "Document metadata is invalid.",
            fields={"tags": "Tags must be a list of strings."},
        )

    unique: dict[str, str] = {}
    for tag in value:
        normalized = tag.strip()
        if not normalized:
            continue
        if len(normalized) > MAX_TAG_LENGTH:
            raise DocumentValidationError(
                "invalid_metadata",
                "Document metadata is invalid.",
                fields={"tags": f"Each tag must be {MAX_TAG_LENGTH} characters or fewer."},
            )
        unique.setdefault(normalized.casefold(), normalized)

    if len(unique) > MAX_TAGS:
        raise DocumentValidationError(
            "invalid_metadata",
            "Document metadata is invalid.",
            fields={"tags": f"Use no more than {MAX_TAGS} tags."},
        )
    return sorted(unique.values(), key=str.casefold)


def validate_upload(uploaded_file) -> ValidatedUpload:
    filename = safe_filename(getattr(uploaded_file, "name", None))
    file_type = FILE_TYPES.get(Path(filename).suffix.lower())
    if file_type is None:
        raise DocumentValidationError(
            "unsupported_file_type",
            "This document type is not supported.",
            status=415,
            fields={"file": "Upload a PDF, DOCX, TXT, Markdown, or CSV file."},
        )

    declared_size = getattr(uploaded_file, "size", None)
    if (
        isinstance(declared_size, int)
        and declared_size > settings.DOCUMENT_MAX_UPLOAD_BYTES
    ):
        raise DocumentValidationError(
            "file_too_large",
            "The uploaded file exceeds the 25 MB limit.",
            status=413,
            fields={"file": "Choose a file no larger than 25 MB."},
        )

    content = uploaded_file.read()
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    if not content:
        raise DocumentValidationError(
            "empty_file",
            "The uploaded file is empty.",
            fields={"file": "Choose a non-empty document."},
        )
    if len(content) > settings.DOCUMENT_MAX_UPLOAD_BYTES:
        raise DocumentValidationError(
            "file_too_large",
            "The uploaded file exceeds the 25 MB limit.",
            status=413,
            fields={"file": "Choose a file no larger than 25 MB."},
        )
    if not file_type.validate(content):
        raise DocumentValidationError(
            "invalid_file_content",
            "The file contents do not match the selected document type.",
            status=415,
            fields={"file": "Choose a valid document with the correct extension."},
        )

    return ValidatedUpload(
        filename=filename,
        content_type=file_type.content_type,
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )
