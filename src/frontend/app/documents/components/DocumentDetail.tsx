"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  deleteDocument,
  getDocument,
  replaceDocument,
  updateDocument,
} from "../lib/api";
import type { DocumentMetadataUpdate, DocumentRecord } from "../types";
import styles from "../documents.module.css";

type DocumentForm = {
  filename: string;
  title: string;
  description: string;
  tagsText: string;
};

type DocumentDetailProps = {
  documentId: string;
  loadDocument?: (id: string) => Promise<DocumentRecord>;
  saveDocument?: (
    id: string,
    metadata: DocumentMetadataUpdate,
  ) => Promise<DocumentRecord>;
  replaceFile?: (
    id: string,
    metadata: DocumentMetadataUpdate,
    file: File,
  ) => Promise<DocumentRecord>;
  removeDocument?: (id: string) => Promise<void>;
};

function formFromDocument(document: DocumentRecord): DocumentForm {
  return {
    filename: document.filename,
    title: document.title,
    description: document.description,
    tagsText: document.tags.join(", "),
  };
}

function metadataFromForm(form: DocumentForm): DocumentMetadataUpdate {
  return {
    filename: form.filename,
    title: form.title,
    description: form.description,
    tags: form.tagsText
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
  };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default function DocumentDetail({
  documentId,
  loadDocument = getDocument,
  saveDocument = updateDocument,
  replaceFile = replaceDocument,
  removeDocument = deleteDocument,
}: DocumentDetailProps) {
  const router = useRouter();
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [form, setForm] = useState<DocumentForm | null>(null);
  const [replacement, setReplacement] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"save" | "replace" | "delete" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    loadDocument(documentId)
      .then((loaded) => {
        if (!active) return;
        setDocument(loaded);
        setForm(formFromDocument(loaded));
        setError("");
      })
      .catch((loadError) => {
        if (active) setError(errorMessage(loadError, "The document could not be loaded."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [documentId, loadDocument]);

  function updateField(field: keyof DocumentForm, value: string) {
    setForm((current) => (current ? { ...current, [field]: value } : current));
  }

  async function saveMetadata() {
    if (!form) return;
    setBusy("save");
    setError("");
    setNotice("");
    try {
      const saved = await saveDocument(documentId, metadataFromForm(form));
      setDocument(saved);
      setForm(formFromDocument(saved));
      setNotice("Metadata saved.");
    } catch (saveError) {
      setError(errorMessage(saveError, "The metadata could not be saved."));
    } finally {
      setBusy(null);
    }
  }

  async function submitReplacement() {
    if (!form || !replacement) return;
    setBusy("replace");
    setError("");
    setNotice("");
    try {
      const saved = await replaceFile(
        documentId,
        metadataFromForm(form),
        replacement,
      );
      setDocument(saved);
      setForm(formFromDocument(saved));
      setReplacement(null);
      setNotice("File replaced.");
    } catch (replaceError) {
      setError(errorMessage(replaceError, "The file could not be replaced."));
    } finally {
      setBusy(null);
    }
  }

  async function confirmDelete() {
    if (!document) return;
    if (!window.confirm(`Delete "${document.title}"? This cannot be undone.`)) return;
    setBusy("delete");
    setError("");
    try {
      await removeDocument(documentId);
      router.push("/documents");
    } catch (deleteError) {
      setError(errorMessage(deleteError, "The document could not be deleted."));
      setBusy(null);
    }
  }

  if (loading) return <div className={styles.statePanel}>Loading document…</div>;
  if (!document || !form) {
    return (
      <div className={styles.statePanel} role="alert">
        <p>{error || "The document could not be loaded."}</p>
        <Link href="/documents">Return to the library</Link>
      </div>
    );
  }

  return (
    <section className={styles.workspace}>
      <div className={styles.detailHeader}>
        <div>
          <Link href="/documents">← Document library</Link>
          <p className={styles.eyebrow}>Managed resource</p>
          <h1>{document.title}</h1>
          <p>{document.filename}</p>
        </div>
        <a className={styles.primaryLink} href={document.downloadUrl} download>
          Download file
        </a>
      </div>

      {(notice || error) && (
        <div
          className={error ? styles.errorNotice : styles.successNotice}
          role={error ? "alert" : "status"}
        >
          {error || notice}
        </div>
      )}

      <div className={styles.detailGrid}>
        <form
          className={styles.editor}
          onSubmit={(event) => {
            event.preventDefault();
            void saveMetadata();
          }}
        >
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Metadata</p>
              <h2>Edit document</h2>
            </div>
          </div>
          <label>
            <span>Filename</span>
            <input
              value={form.filename}
              onChange={(event) => updateField("filename", event.target.value)}
              maxLength={255}
              required
            />
          </label>
          <label>
            <span>Title</span>
            <input
              value={form.title}
              onChange={(event) => updateField("title", event.target.value)}
              maxLength={255}
              required
            />
          </label>
          <label>
            <span>Description</span>
            <textarea
              value={form.description}
              onChange={(event) => updateField("description", event.target.value)}
              maxLength={5000}
              rows={5}
            />
          </label>
          <label>
            <span>Tags</span>
            <input
              value={form.tagsText}
              onChange={(event) => updateField("tagsText", event.target.value)}
              placeholder="rag, finance, policy"
            />
          </label>
          <button type="submit" disabled={busy !== null}>
            {busy === "save" ? "Saving…" : "Save metadata"}
          </button>
        </form>

        <aside className={styles.metadataCard}>
          <p className={styles.eyebrow}>System metadata</p>
          <dl>
            <div>
              <dt>Content type</dt>
              <dd>{document.contentType}</dd>
            </div>
            <div>
              <dt>Size</dt>
              <dd>{document.size.toLocaleString()} bytes</dd>
            </div>
            <div>
              <dt>SHA-256</dt>
              <dd className={styles.checksum}>{document.sha256}</dd>
            </div>
            <div>
              <dt>Uploaded</dt>
              <dd>{new Date(document.createdAt).toLocaleString()}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{new Date(document.updatedAt).toLocaleString()}</dd>
            </div>
          </dl>
        </aside>
      </div>

      <section className={styles.dangerGrid}>
        <div className={styles.editor}>
          <p className={styles.eyebrow}>File contents</p>
          <h2>Replace file</h2>
          <p>The UUID storage path changes; the document record and metadata remain.</p>
          <label>
            <span>Replacement file</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md,.markdown,.csv"
              onChange={(event) => setReplacement(event.target.files?.[0] ?? null)}
            />
          </label>
          <button
            type="button"
            onClick={() => void submitReplacement()}
            disabled={!replacement || busy !== null}
          >
            {busy === "replace" ? "Replacing…" : "Replace file"}
          </button>
        </div>

        <div className={styles.dangerCard}>
          <p className={styles.eyebrow}>Danger zone</p>
          <h2>Delete document</h2>
          <p>Delete the SQLite record and the stored file permanently.</p>
          <button type="button" onClick={() => void confirmDelete()} disabled={busy !== null}>
            {busy === "delete" ? "Deleting…" : "Delete document"}
          </button>
        </div>
      </section>
    </section>
  );
}
