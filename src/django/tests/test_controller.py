import importlib


def test_app_imports_base_controller_successfully():
    controllers = importlib.import_module("app.controller")

    assert controllers.BaseController is not None
