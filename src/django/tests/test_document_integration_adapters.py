import pytest
from django.core.exceptions import ImproperlyConfigured

from document_integrations.adapters.django_documents import (
    DjangoDocumentRevisionRepository,
    SystemClock,
)
from document_integrations.adapters.import_string import load_configured_adapter


class ConfiguredAdapter:
    def handle(self, event):
        return None


def test_loader_constructs_configured_adapter(settings):
    settings.TEST_DOCUMENT_ADAPTER = f"{__name__}.ConfiguredAdapter"

    loaded = load_configured_adapter(
        "TEST_DOCUMENT_ADAPTER",
        required_methods=("handle",),
    )

    assert isinstance(loaded, ConfiguredAdapter)


def test_loader_rejects_missing_setting(settings):
    settings.TEST_DOCUMENT_ADAPTER = ""

    with pytest.raises(ImproperlyConfigured, match="TEST_DOCUMENT_ADAPTER"):
        load_configured_adapter(
            "TEST_DOCUMENT_ADAPTER",
            required_methods=("handle",),
        )


def test_system_clock_returns_aware_utc_time():
    assert SystemClock().now().tzinfo is not None


@pytest.mark.django_db(databases=["documents"])
def test_django_revision_repository_uses_public_revision_query():
    assert DjangoDocumentRevisionRepository().list_current() == []
