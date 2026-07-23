from collections.abc import Sequence

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def load_configured_adapter(
    setting_name: str,
    *,
    required_methods: Sequence[str],
):
    dotted_path = getattr(settings, setting_name, "")
    if not isinstance(dotted_path, str) or not dotted_path.strip():
        raise ImproperlyConfigured(f"{setting_name} must be configured.")
    try:
        adapter_class = import_string(dotted_path)
        adapter = adapter_class()
    except (ImportError, AttributeError, TypeError) as error:
        raise ImproperlyConfigured(
            f"{setting_name} does not identify a constructible adapter."
        ) from error
    missing = [name for name in required_methods if not callable(getattr(adapter, name, None))]
    if missing:
        joined = ", ".join(missing)
        raise ImproperlyConfigured(
            f"{setting_name} adapter is missing required methods: {joined}."
        )
    return adapter
