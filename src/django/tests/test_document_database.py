import json
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from documents.models import Document
from documents.router import DocumentDatabaseRouter


def test_documents_database_is_separate_sqlite():
    script = """
import json
from app import settings
database = settings.DATABASES["documents"]
print(json.dumps({
    "engine": database["ENGINE"],
    "name": str(database["NAME"]),
    "dependencies": database["TEST"]["DEPENDENCIES"],
}))
"""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    database = json.loads(result.stdout)

    assert database["engine"] == "django.db.backends.sqlite3"
    assert Path(database["name"]).name == "metadata.sqlite3"
    assert database["dependencies"] == []
    assert settings.DOCUMENT_DATA_ROOT.is_dir()
    assert settings.DOCUMENT_MAX_UPLOAD_BYTES == 25 * 1024 * 1024


def test_router_isolates_document_models():
    router = DocumentDatabaseRouter()

    assert router.db_for_read(Document) == "documents"
    assert router.db_for_write(Document) == "documents"
    assert router.allow_migrate("documents", "documents", model_name="document") is True
    assert router.allow_migrate("default", "documents", model_name="document") is False
    assert router.allow_migrate("documents", "auth", model_name="user") is False


@pytest.mark.django_db(databases=["documents"])
def test_document_defaults_are_stored_in_sqlite():
    document = Document.objects.create(
        file="a1b2c3",
        filename="report.txt",
        title="report",
        content_type="text/plain",
        size=6,
        sha256="0" * 64,
    )

    loaded = Document.objects.get(pk=document.pk)
    assert loaded.description == ""
    assert loaded.tags == []
    assert loaded._state.db == "documents"
