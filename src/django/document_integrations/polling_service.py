import logging

from .contracts import ReconciliationReport
from .ports import (
    DocumentRevisionRepository,
    RagRevisionStateReader,
    RagSyncCommandSink,
)

logger = logging.getLogger(__name__)


class RevisionPollingService:
    def __init__(
        self,
        *,
        documents: DocumentRevisionRepository,
        rag_state: RagRevisionStateReader,
        commands: RagSyncCommandSink,
    ):
        self.documents = documents
        self.rag_state = rag_state
        self.commands = commands

    def reconcile(self, *, dry_run: bool = False) -> ReconciliationReport:
        sources = {item.document_id: item for item in self.documents.list_current()}
        indexed = {item.document_id: item for item in self.rag_state.list_indexed()}
        requested_sync = 0
        requested_delete = 0
        current = 0
        failed = 0

        for document_id in sorted(sources, key=str):
            snapshot = sources[document_id]
            indexed_revision = indexed.get(document_id)
            needs_sync = indexed_revision is None or (
                indexed_revision.content_revision != snapshot.content_revision
                or indexed_revision.source_sha256 != snapshot.source_sha256
                or indexed_revision.source_updated_at != snapshot.updated_at
            )
            if not needs_sync:
                current += 1
                continue
            requested_sync += 1
            if dry_run:
                continue
            try:
                self.commands.request_sync(snapshot)
            except Exception:
                failed += 1
                logger.error(
                    "Document synchronization request failed for %s.",
                    document_id,
                )

        for document_id in sorted(set(indexed) - set(sources), key=str):
            requested_delete += 1
            if dry_run:
                continue
            try:
                self.commands.request_delete(document_id)
            except Exception:
                failed += 1
                logger.error(
                    "Document deletion request failed for %s.",
                    document_id,
                )

        return ReconciliationReport(
            source_count=len(sources),
            indexed_count=len(indexed),
            requested_sync=requested_sync,
            requested_delete=requested_delete,
            current=current,
            failed=failed,
        )
