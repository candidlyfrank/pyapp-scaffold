import io
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.validation import (
    DOCX_CONTENT_TYPE,
    DocumentValidationError,
    normalize_tags,
    validate_upload,
)


def docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<document />")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("name", "content", "content_type"),
    [
        ("report.pdf", b"%PDF-1.7\nbody", "application/pdf"),
        ("report.docx", docx_bytes(), DOCX_CONTENT_TYPE),
        ("notes.txt", b"hello", "text/plain"),
        ("notes.md", b"# Heading", "text/markdown"),
        ("data.csv", b"name,value\none,1\n", "text/csv"),
    ],
)
def test_validates_supported_document_content(name, content, content_type):
    upload = SimpleUploadedFile(name, content, content_type="application/octet-stream")

    validated = validate_upload(upload)

    assert validated.filename == name
    assert validated.content == content
    assert validated.content_type == content_type
    assert validated.size == len(content)
    assert len(validated.sha256) == 64


def test_rejects_extension_content_mismatch():
    upload = SimpleUploadedFile("fake.pdf", b"plain text", content_type="application/pdf")

    with pytest.raises(DocumentValidationError) as error:
        validate_upload(upload)

    assert error.value.code == "invalid_file_content"
    assert error.value.status == 415


def test_rejects_oversized_file(settings):
    class OversizedUpload:
        name = "notes.txt"
        size = 4

        def read(self):
            raise AssertionError("Oversized files must be rejected before reading.")

    settings.DOCUMENT_MAX_UPLOAD_BYTES = 3
    upload = OversizedUpload()

    with pytest.raises(DocumentValidationError) as error:
        validate_upload(upload)

    assert error.value.code == "file_too_large"
    assert error.value.status == 413


@pytest.mark.parametrize("name", ["malware.exe", "README", "\x00.txt"])
def test_rejects_unsupported_or_unsafe_filenames(name):
    upload = SimpleUploadedFile(name, b"content")

    with pytest.raises(DocumentValidationError) as error:
        validate_upload(upload)

    assert error.value.code in {"invalid_filename", "unsupported_file_type"}


def test_uses_safe_basename_for_path_like_names():
    upload = SimpleUploadedFile("folder/notes.txt", b"hello")

    assert validate_upload(upload).filename == "notes.txt"


def test_tags_are_trimmed_deduplicated_and_sorted():
    assert normalize_tags([" RAG ", "cms", "rag"]) == ["cms", "RAG"]


def test_rejects_invalid_tag_shape():
    with pytest.raises(DocumentValidationError) as error:
        normalize_tags("rag")

    assert error.value.fields == {"tags": "Tags must be a list of strings."}
