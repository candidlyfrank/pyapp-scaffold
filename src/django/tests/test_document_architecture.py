import ast
from pathlib import Path


DJANGO_ROOT = Path(__file__).resolve().parents[1]


def imported_roots(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_documents_never_imports_integration_or_rag_packages():
    forbidden = {"document_integrations", "rag"}

    for path in (DJANGO_ROOT / "documents").rglob("*.py"):
        assert imported_roots(path).isdisjoint(forbidden), path


def test_core_integration_services_do_not_import_django_orm():
    core_files = [
        DJANGO_ROOT / "document_integrations" / "contracts.py",
        DJANGO_ROOT / "document_integrations" / "ports.py",
        DJANGO_ROOT / "document_integrations" / "callback_service.py",
        DJANGO_ROOT / "document_integrations" / "polling_service.py",
    ]

    for path in core_files:
        assert "django" not in imported_roots(path), path
