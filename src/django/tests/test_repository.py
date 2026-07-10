import importlib


def test_app_imports_base_repository_successfully():
    repository = importlib.import_module("app.repository")

    assert repository.BaseRepository is not None
