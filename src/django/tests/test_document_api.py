import json
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import Client
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from documents.models import Document
from documents.services import create_document

COLLECTION_URL = "/api/documents/"


@pytest.fixture(autouse=True)
def document_media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


def make_document(name="notes.txt", content=b"hello"):
    return create_document(SimpleUploadedFile(name, content))


@pytest.mark.django_db(databases=["documents"])
def test_post_upload_then_get_list(client):
    client.get(COLLECTION_URL)
    response = client.post(
        COLLECTION_URL,
        {"files": [SimpleUploadedFile("notes.txt", b"hello")]},
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )

    assert response.status_code == 201
    created = response.json()["results"][0]["document"]
    listed = client.get(COLLECTION_URL).json()["documents"]
    assert listed[0]["id"] == created["id"]
    assert listed[0]["filename"] == "notes.txt"
    assert listed[0]["downloadUrl"].endswith(f"/{created['id']}/download/")


@pytest.mark.django_db(databases=["documents"])
def test_mixed_upload_reports_each_result(client):
    response = client.post(
        COLLECTION_URL,
        {
            "files": [
                SimpleUploadedFile("notes.txt", b"hello"),
                SimpleUploadedFile("fake.pdf", b"not a pdf"),
            ]
        },
    )

    assert response.status_code == 207
    assert [result["status"] for result in response.json()["results"]] == [
        "uploaded",
        "error",
    ]
    assert response.json()["results"][1]["error"]["code"] == "invalid_file_content"


@pytest.mark.django_db(databases=["documents"])
def test_single_invalid_upload_preserves_validation_status(client):
    response = client.post(
        COLLECTION_URL,
        {"files": [SimpleUploadedFile("fake.pdf", b"not a pdf")]},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_file_content"


@pytest.mark.django_db(databases=["documents"])
def test_list_search_filter_tag_and_ordering(client):
    first = make_document("alpha.txt", b"alpha")
    first.title = "Research Alpha"
    first.tags = ["RAG"]
    first.save(using="documents")
    second = make_document("beta.md", b"# beta")
    second.title = "Beta"
    second.tags = ["CMS"]
    second.save(using="documents")

    search = client.get(COLLECTION_URL, {"q": "alpha"}).json()["documents"]
    filtered = client.get(
        COLLECTION_URL,
        {"content_type": "text/markdown", "tag": "cms"},
    ).json()["documents"]
    ordered = client.get(COLLECTION_URL, {"ordering": "filename"}).json()["documents"]

    assert [item["id"] for item in search] == [str(first.id)]
    assert [item["id"] for item in filtered] == [str(second.id)]
    assert [item["filename"] for item in ordered] == ["alpha.txt", "beta.md"]


@pytest.mark.django_db(databases=["documents"])
def test_list_rejects_unknown_ordering(client):
    response = client.get(COLLECTION_URL, {"ordering": "sha256"})

    assert response.status_code == 400
    assert response.json()["error"]["fields"] == {
        "ordering": "Choose a supported ordering value."
    }


@pytest.mark.django_db(databases=["documents"])
def test_get_and_patch_document_metadata(client):
    document = make_document()
    url = f"{COLLECTION_URL}{document.id}/"

    detail = client.get(url)
    updated = client.patch(
        url,
        data=json.dumps(
            {
                "filename": "knowledge.txt",
                "title": "Knowledge",
                "description": "RAG source",
                "tags": ["rag", "CMS"],
            }
        ),
        content_type="application/json",
    )

    assert detail.status_code == 200
    assert detail.json()["sha256"] == document.sha256
    assert updated.status_code == 200
    assert updated.json()["filename"] == "knowledge.txt"
    assert updated.json()["tags"] == ["CMS", "rag"]


@pytest.mark.django_db(databases=["documents"])
def test_multipart_patch_replaces_file(client):
    document = make_document()
    url = f"{COLLECTION_URL}{document.id}/"
    body = encode_multipart(
        BOUNDARY,
        {
            "metadata": json.dumps({"filename": "replacement.md"}),
            "file": SimpleUploadedFile("replacement.md", b"# replacement"),
        },
    )

    response = client.generic("PATCH", url, body, content_type=MULTIPART_CONTENT)

    document.refresh_from_db(using="documents")
    assert response.status_code == 200
    assert document.filename == "replacement.md"
    assert document.content_type == "text/markdown"
    with document.file.open("rb") as stored:
        assert stored.read() == b"# replacement"


@pytest.mark.django_db(databases=["documents"])
def test_download_uses_editable_filename(client):
    document = make_document()
    document.filename = "renamed notes.txt"
    document.save(using="documents")

    response = client.get(f"{COLLECTION_URL}{document.id}/download/")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert 'filename="renamed notes.txt"' in response.headers["Content-Disposition"]
    assert b"".join(response.streaming_content) == b"hello"


@pytest.mark.django_db(databases=["documents"])
def test_delete_removes_record_and_file(client):
    document = make_document()
    storage = document.file.storage
    storage_name = document.file.name

    response = client.delete(f"{COLLECTION_URL}{document.id}/")

    assert response.status_code == 204
    assert not Document.objects.filter(pk=document.id).exists()
    assert not storage.exists(storage_name)


@pytest.mark.django_db(databases=["documents"])
def test_missing_record_and_file_return_json_404(client):
    document = make_document()
    document.file.storage.delete(document.file.name)

    missing_file = client.get(f"{COLLECTION_URL}{document.id}/download/")
    missing_record = client.get(f"{COLLECTION_URL}00000000-0000-0000-0000-000000000000/")

    assert missing_file.status_code == 404
    assert missing_file.json()["error"]["code"] == "stored_file_missing"
    assert missing_record.status_code == 404
    assert missing_record.json()["error"]["code"] == "document_not_found"


@pytest.mark.django_db(databases=["documents"])
def test_mutations_require_csrf():
    client = Client(enforce_csrf_checks=True)
    document = make_document()

    rejected_upload = client.post(COLLECTION_URL, {})
    assert rejected_upload.status_code == 403
    assert rejected_upload.json()["error"]["code"] == "csrf_failed"
    assert (
        client.patch(
            f"{COLLECTION_URL}{document.id}/",
            data=json.dumps({"title": "Changed"}),
            content_type="application/json",
        ).status_code
        == 403
    )
    assert client.delete(f"{COLLECTION_URL}{document.id}/").status_code == 403


@pytest.mark.django_db(databases=["documents"])
def test_persistence_failures_return_structured_json(client):
    document = make_document()

    with patch("documents.views._list_documents", side_effect=DatabaseError):
        listing = client.get(COLLECTION_URL)
    with patch("documents.views.create_document", side_effect=DatabaseError):
        upload = client.post(
            COLLECTION_URL,
            {"files": [SimpleUploadedFile("notes.txt", b"hello")]},
        )
    with patch("documents.views.update_document", side_effect=OSError):
        update = client.patch(
            f"{COLLECTION_URL}{document.id}/",
            data=json.dumps({"title": "Changed"}),
            content_type="application/json",
        )
    with patch("documents.views.delete_document", side_effect=OSError):
        deletion = client.delete(f"{COLLECTION_URL}{document.id}/")

    for response in [listing, upload, update, deletion]:
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "document_persistence_failed"


@pytest.mark.django_db(databases=["documents"])
def test_unsupported_methods_return_structured_json(client):
    response = client.put(
        COLLECTION_URL,
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET, POST"
    assert response.json()["error"]["code"] == "method_not_allowed"
