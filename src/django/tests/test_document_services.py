import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import Document, DocumentOutboxEvent
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


def outbox_events(document_id):
    return list(
        DocumentOutboxEvent.objects.filter(document_id=document_id).order_by(
            "occurred_at",
            "id",
        )
    )


@pytest.mark.django_db(databases=["documents"])
def test_create_appends_created_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    event = outbox_events(document.id)[0]
    assert event.event_type == DocumentOutboxEvent.EventType.CREATED
    assert event.content_revision == 1
    assert event.source_sha256 == document.sha256
    assert event.payload == {
        "filename": "notes.txt",
        "content_type": "text/plain",
        "size": 5,
    }


@pytest.mark.django_db(databases=["documents"])
def test_metadata_change_emits_event_without_incrementing_content_revision(
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    updated = update_document(document, {"title": "Knowledge", "tags": ["rag"]})

    events = outbox_events(document.id)
    assert updated.content_revision == 1
    assert [event.event_type for event in events] == [
        DocumentOutboxEvent.EventType.CREATED,
        DocumentOutboxEvent.EventType.METADATA_UPDATED,
    ]
    assert events[-1].payload == {"changed_fields": ["tags", "title"]}


@pytest.mark.django_db(databases=["documents"])
def test_noop_metadata_update_emits_no_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    update_document(document, {"title": document.title})

    assert len(outbox_events(document.id)) == 1


@pytest.mark.django_db(databases=["documents"])
def test_replacement_increments_revision_and_emits_content_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))

    updated = update_document(
        document,
        {},
        SimpleUploadedFile("new.md", b"# new"),
    )

    event = outbox_events(document.id)[-1]
    assert updated.content_revision == 2
    assert event.event_type == DocumentOutboxEvent.EventType.CONTENT_REPLACED
    assert event.content_revision == 2
    assert event.source_sha256 == updated.sha256


@pytest.mark.django_db(databases=["documents"])
def test_replacement_with_metadata_change_emits_both_events(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))

    update_document(
        document,
        {"title": "Replacement"},
        SimpleUploadedFile("new.md", b"# new"),
    )

    assert [event.event_type for event in outbox_events(document.id)] == [
        DocumentOutboxEvent.EventType.CREATED,
        DocumentOutboxEvent.EventType.CONTENT_REPLACED,
        DocumentOutboxEvent.EventType.METADATA_UPDATED,
    ]


@pytest.mark.django_db(databases=["documents"])
def test_delete_event_survives_document_deletion(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    document_id = document.id

    delete_document(document)

    deleted = DocumentOutboxEvent.objects.get(
        document_id=document_id,
        event_type=DocumentOutboxEvent.EventType.DELETED,
    )
    assert deleted.content_revision == 1
    assert not Document.objects.filter(pk=document_id).exists()


@pytest.mark.django_db(databases=["documents"])
def test_create_removes_file_when_outbox_insert_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            create_document(SimpleUploadedFile("notes.txt", b"hello"))

    assert not Document.objects.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db(databases=["documents"])
def test_replace_rolls_back_record_and_new_file_when_outbox_insert_fails(
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))
    old_name = document.file.name

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            update_document(document, {}, SimpleUploadedFile("new.md", b"# new"))

    document.refresh_from_db(using="documents")
    assert document.file.name == old_name
    assert document.content_revision == 1
    assert [path.name for path in tmp_path.iterdir()] == [old_name]


@pytest.mark.django_db(databases=["documents"])
def test_delete_restores_file_when_outbox_insert_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    storage_name = document.file.name

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            delete_document(document)

    assert Document.objects.filter(pk=document.id).exists()
    assert document.file.storage.exists(storage_name)
