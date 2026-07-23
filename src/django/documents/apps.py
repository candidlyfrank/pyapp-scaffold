from django.apps import AppConfig
from django.conf import settings


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"

    def ready(self):
        settings.DOCUMENT_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        settings.DOCUMENT_FILES_ROOT.mkdir(parents=True, exist_ok=True)
