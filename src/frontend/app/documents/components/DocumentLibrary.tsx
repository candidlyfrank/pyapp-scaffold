"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { listDocuments } from "../lib/api";
import type { DocumentQuery, DocumentRecord } from "../types";
import styles from "../documents.module.css";

type DocumentLibraryProps = {
  loadDocuments?: (query?: DocumentQuery) => Promise<DocumentRecord[]>;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export default function DocumentLibrary({
  loadDocuments = listDocuments,
}: DocumentLibraryProps) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [query, setQuery] = useState("");
  const [contentType, setContentType] = useState("");
  const [tag, setTag] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const requestSequence = useRef(0);

  useEffect(() => {
    const sequence = ++requestSequence.current;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const result = await loadDocuments({
          q: query,
          contentType,
          tag,
          ordering,
        });
        if (requestSequence.current === sequence) setDocuments(result);
      } catch (loadError) {
        if (requestSequence.current === sequence) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "The document library could not be loaded.",
          );
        }
      } finally {
        if (requestSequence.current === sequence) setLoading(false);
      }
    }, query || tag ? 200 : 0);
    return () => window.clearTimeout(timer);
  }, [contentType, loadDocuments, ordering, query, revision, tag]);

  return (
    <section className={styles.workspace}>
      <div className={styles.libraryHeader}>
        <div className={styles.hero}>
          <p className={styles.eyebrow}>Content catalogue</p>
          <h1>Document library</h1>
          <p>Browse the live metadata held by Django in the document SQLite database.</p>
        </div>
        <Link className={styles.primaryLink} href="/documents/upload">
          Upload documents
        </Link>
      </div>

      <aside className={styles.warning}>
        <strong>Local development only.</strong> Document access is currently
        unauthenticated.
      </aside>

      <div className={styles.filters}>
        <label className={styles.searchField}>
          <span>Search documents</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Title or filename"
          />
        </label>
        <label>
          <span>Document type</span>
          <select value={contentType} onChange={(event) => setContentType(event.target.value)}>
            <option value="">All types</option>
            <option value="application/pdf">PDF</option>
            <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">
              DOCX
            </option>
            <option value="text/plain">TXT</option>
            <option value="text/markdown">Markdown</option>
            <option value="text/csv">CSV</option>
          </select>
        </label>
        <label>
          <span>Tag</span>
          <input value={tag} onChange={(event) => setTag(event.target.value)} />
        </label>
        <label>
          <span>Sort documents</span>
          <select value={ordering} onChange={(event) => setOrdering(event.target.value)}>
            <option value="-created_at">Newest uploaded</option>
            <option value="created_at">Oldest uploaded</option>
            <option value="-updated_at">Recently updated</option>
            <option value="updated_at">Least recently updated</option>
            <option value="filename">Filename A–Z</option>
            <option value="-filename">Filename Z–A</option>
          </select>
        </label>
      </div>

      {loading && <div className={styles.statePanel}>Loading documents…</div>}
      {!loading && error && (
        <div className={styles.statePanel} role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => setRevision((value) => value + 1)}>
            Try again
          </button>
        </div>
      )}
      {!loading && !error && documents.length === 0 && (
        <div className={styles.statePanel}>
          <h2>Your document library is empty.</h2>
          <p>Upload a source to start building your managed knowledge base.</p>
          <Link href="/documents/upload">Upload your first document</Link>
        </div>
      )}
      {!loading && !error && documents.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.libraryTable}>
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th>Size</th>
                <th>Tags</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td data-label="Document">
                    <Link className={styles.documentLink} href={`/documents/${document.id}`}>
                      {document.title}
                    </Link>
                    <span>{document.filename}</span>
                  </td>
                  <td data-label="Type">{document.contentType}</td>
                  <td data-label="Size">{formatSize(document.size)}</td>
                  <td data-label="Tags">
                    <div className={styles.tags}>
                      {document.tags.length
                        ? document.tags.map((item) => <span key={item}>{item}</span>)
                        : "—"}
                    </div>
                  </td>
                  <td data-label="Updated">{formatDate(document.updatedAt)}</td>
                  <td data-label="Actions">
                    <a href={document.downloadUrl} download>
                      Download {document.title}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
