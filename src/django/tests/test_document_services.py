import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import Document
from documents.services import create_document, delete_document, update_document


@pytest.mark.django_db(databases=["documents"])
def test_create_document_writes_uuid_file_and_checksum(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    upload = SimpleUploadedFile("notes.txt", b"hello")

    document = create_document(upload)

    assert document.filename == "notes.txt"
    assert document.title == "notes"
    assert document.sha256 == hashlib.sha256(b"hello").hexdigest()
    assert Path(document.file.name).name != "notes.txt"
    with document.file.open("rb") as stored:
        assert stored.read() == b"hello"


@pytest.mark.django_db(databases=["documents"])
def test_metadata_update_normalizes_values_without_renaming_storage(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    storage_name = document.file.name

    updated = update_document(
        document,
        {
            "filename": "renamed notes.txt",
            "title": " Knowledge Notes ",
            "description": "Useful context",
            "tags": [" RAG ", "cms", "rag"],
        },
    )

    assert updated.file.name == storage_name
    assert updated.filename == "renamed notes.txt"
    assert updated.title == "Knowledge Notes"
    assert updated.tags == ["cms", "RAG"]


@pytest.mark.django_db(databases=["documents"])
def test_replacement_removes_old_file_after_save(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("old.txt", b"old"))
    old_name = document.file.name

    updated = update_document(
        document,
        {"filename": "renamed.md"},
        SimpleUploadedFile("new.md", b"# new"),
    )

    assert updated.filename == "renamed.md"
    with updated.file.open("rb") as stored:
        assert stored.read() == b"# new"
    assert not updated.file.storage.exists(old_name)


@pytest.mark.django_db(databases=["documents"])
def test_replacement_cleanup_failure_does_not_report_committed_update_as_failed(
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("old.txt", b"old"))
    old_name = document.file.name
    storage = document.file.storage

    with patch.object(storage, "delete", side_effect=OSError("cleanup unavailable")):
        updated = update_document(
            document,
            {"filename": "new.md"},
            SimpleUploadedFile("new.md", b"# new"),
        )

    updated.refresh_from_db(using="documents")
    assert updated.file.name != old_name
    with updated.file.open("rb") as stored:
        assert stored.read() == b"# new"


@pytest.mark.django_db(databases=["documents"])
def test_create_cleans_up_new_file_when_database_save_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    with patch.object(Document, "save", side_effect=RuntimeError("database unavailable")):
        with pytest.raises(RuntimeError, match="database unavailable"):
            create_document(SimpleUploadedFile("notes.txt", b"hello"))

    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db(databases=["documents"])
def test_replacement_cleans_up_new_file_when_database_save_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"original"))
    old_name = document.file.name

    with patch.object(Document, "save", side_effect=RuntimeError("database unavailable")):
        with pytest.raises(RuntimeError, match="database unavailable"):
            update_document(
                document,
                {"filename": "replacement.md"},
                SimpleUploadedFile("replacement.md", b"# replacement"),
            )

    document.refresh_from_db(using="documents")
    assert document.file.name == old_name
    assert document.file.storage.exists(old_name)
    assert [path.name for path in tmp_path.iterdir()] == [old_name]


@pytest.mark.django_db(databases=["documents"])
def test_delete_removes_database_record_and_file(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    document_id = document.id
    storage_name = document.file.name
    storage = document.file.storage

    delete_document(document)

    assert not Document.objects.filter(pk=document_id).exists()
    assert not storage.exists(storage_name)


@pytest.mark.django_db(databases=["documents"])
def test_delete_restores_file_when_database_delete_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    storage_name = document.file.name
    storage = document.file.storage

    with patch.object(Document, "delete", side_effect=RuntimeError("database unavailable")):
        with pytest.raises(RuntimeError, match="database unavailable"):
            delete_document(document)

    assert Document.objects.filter(pk=document.id).exists()
    assert storage.exists(storage_name)
    with storage.open(storage_name, "rb") as restored:
        assert restored.read() == b"hello"
