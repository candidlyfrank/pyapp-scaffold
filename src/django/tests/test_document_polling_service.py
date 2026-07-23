from datetime import UTC, datetime, timedelta
from uuid import uuid4

from document_integrations.contracts import IndexedDocumentRevision
from document_integrations.polling_service import RevisionPollingService
from documents.contracts import DocumentRevisionSnapshot

NOW = datetime(2026, 7, 23, 12, tzinfo=UTC)


def source(document_id, revision=1, checksum="a", updated_at=NOW):
    return DocumentRevisionSnapshot(
        document_id=document_id,
        content_revision=revision,
        source_sha256=checksum * 64,
        content_type="text/plain",
        size=5,
        updated_at=updated_at,
    )


def indexed(document_id, revision=1, checksum="a", updated_at=NOW):
    return IndexedDocumentRevision(
        document_id=document_id,
        content_revision=revision,
        source_sha256=checksum * 64,
        source_updated_at=updated_at,
    )


class FakeDocuments:
    def __init__(self, values):
        self.values = values

    def list_current(self):
        return self.values


class FakeRagState:
    def __init__(self, values):
        self.values = values

    def list_indexed(self):
        return self.values


class FakeSink:
    def __init__(self, fail_ids=None):
        self.fail_ids = set(fail_ids or [])
        self.synced = []
        self.deleted = []

    def request_sync(self, snapshot):
        if snapshot.document_id in self.fail_ids:
            raise RuntimeError("sync failed")
        self.synced.append(snapshot.document_id)

    def request_delete(self, document_id):
        if document_id in self.fail_ids:
            raise RuntimeError("delete failed")
        self.deleted.append(document_id)


def test_reconciles_missing_stale_current_metadata_and_deleted_documents():
    missing = uuid4()
    stale = uuid4()
    metadata_stale = uuid4()
    current = uuid4()
    deleted = uuid4()
    sources = [
        source(missing),
        source(stale, revision=2, checksum="b"),
        source(metadata_stale, updated_at=NOW + timedelta(minutes=1)),
        source(current),
    ]
    indexed_values = [
        indexed(stale),
        indexed(metadata_stale),
        indexed(current),
        indexed(deleted),
    ]
    sink = FakeSink()
    service = RevisionPollingService(
        documents=FakeDocuments(sources),
        rag_state=FakeRagState(indexed_values),
        commands=sink,
    )

    report = service.reconcile()

    assert set(sink.synced) == {missing, stale, metadata_stale}
    assert sink.deleted == [deleted]
    assert report.requested_sync == 3
    assert report.requested_delete == 1
    assert report.current == 1
    assert report.failed == 0


def test_dry_run_reports_without_invoking_sink_and_collects_item_failures():
    first = uuid4()
    second = uuid4()
    sink = FakeSink(fail_ids={second})
    service = RevisionPollingService(
        documents=FakeDocuments([source(first), source(second)]),
        rag_state=FakeRagState([]),
        commands=sink,
    )

    dry = service.reconcile(dry_run=True)
    actual = service.reconcile()

    assert dry.requested_sync == 2
    assert sink.synced == [first]
    assert actual.failed == 1
