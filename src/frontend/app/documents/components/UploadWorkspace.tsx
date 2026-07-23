"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { uploadDocument } from "../lib/api";
import type { DocumentRecord } from "../types";
import styles from "../documents.module.css";

const MAX_FILE_SIZE = 25 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md", ".markdown", ".csv"];
const ACCEPT_VALUE = ACCEPTED_EXTENSIONS.join(",");

type QueueStatus = "ready" | "uploading" | "uploaded" | "error";

type QueueItem = {
  id: string;
  file: File;
  progress: number;
  status: QueueStatus;
  error?: string;
  clientError?: boolean;
  document?: DocumentRecord;
};

type UploadFunction = (
  file: File,
  onProgress: (progress: number) => void,
) => Promise<DocumentRecord>;

type UploadWorkspaceProps = {
  uploadFile?: UploadFunction;
};

let queueSequence = 0;

function validateFile(file: File): string | undefined {
  const lowerName = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
    return "This file type is not supported.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "This file is larger than 25 MB.";
  }
  return undefined;
}

function createQueueItem(file: File): QueueItem {
  const error = validateFile(file);
  queueSequence += 1;
  return {
    id: `${file.name}-${file.lastModified}-${queueSequence}`,
    file,
    progress: 0,
    status: error ? "error" : "ready",
    error,
    clientError: Boolean(error),
  };
}

export default function UploadWorkspace({
  uploadFile = uploadDocument,
}: UploadWorkspaceProps) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | File[]) {
    setItems((current) => [...current, ...Array.from(files, createQueueItem)]);
  }

  async function uploadItem(item: QueueItem) {
    if (item.clientError) return;
    setItems((current) =>
      current.map((candidate) =>
        candidate.id === item.id
          ? { ...candidate, status: "uploading", progress: 0, error: undefined }
          : candidate,
      ),
    );
    try {
      const document = await uploadFile(item.file, (progress) => {
        setItems((current) =>
          current.map((candidate) =>
            candidate.id === item.id ? { ...candidate, progress } : candidate,
          ),
        );
      });
      setItems((current) =>
        current.map((candidate) =>
          candidate.id === item.id
            ? {
                ...candidate,
                status: "uploaded",
                progress: 100,
                document,
                error: undefined,
              }
            : candidate,
        ),
      );
    } catch (error) {
      setItems((current) =>
        current.map((candidate) =>
          candidate.id === item.id
            ? {
                ...candidate,
                status: "error",
                error:
                  error instanceof Error
                    ? error.message
                    : "The document could not be uploaded.",
                clientError: false,
              }
            : candidate,
        ),
      );
    }
  }

  async function uploadAll() {
    const pending = items.filter(
      (item) => item.status === "ready" || (item.status === "error" && !item.clientError),
    );
    await Promise.all(pending.map(uploadItem));
  }

  return (
    <section className={styles.workspace}>
      <div className={styles.hero}>
        <p className={styles.eyebrow}>Document ingestion</p>
        <h1>Upload knowledge sources</h1>
        <p>
          Add PDF, DOCX, TXT, Markdown, and CSV files. Django validates and stores
          every document for future retrieval and RAG workflows.
        </p>
      </div>

      <aside className={styles.warning}>
        <strong>Local development only.</strong> Uploads are currently unauthenticated.
        Add authorization before exposing this workspace publicly.
      </aside>

      <div
        className={styles.dropzone}
        data-testid="document-dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          addFiles(event.dataTransfer.files);
        }}
      >
        <div className={styles.dropIcon} aria-hidden="true">
          ↑
        </div>
        <h2>Drop documents here</h2>
        <p>or choose files from your computer</p>
        <button type="button" onClick={() => inputRef.current?.click()}>
          Choose files
        </button>
        <input
          ref={inputRef}
          className={styles.srOnly}
          type="file"
          multiple
          accept={ACCEPT_VALUE}
          aria-label="Choose documents"
          onChange={(event) => {
            if (event.target.files) addFiles(event.target.files);
            event.target.value = "";
          }}
        />
        <small>Maximum 25 MB per file</small>
      </div>

      {items.length > 0 && (
        <section className={styles.queue} aria-label="Upload queue">
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Queue</p>
              <h2>{items.length} selected</h2>
            </div>
            <button
              type="button"
              onClick={uploadAll}
              disabled={!items.some(
                (item) =>
                  item.status === "ready" ||
                  (item.status === "error" && !item.clientError),
              )}
            >
              Upload all
            </button>
          </div>

          <div className={styles.queueList}>
            {items.map((item) => (
              <article className={styles.queueItem} key={item.id}>
                <div className={styles.fileBadge} aria-hidden="true">
                  {item.file.name.split(".").pop()?.slice(0, 4).toUpperCase()}
                </div>
                <div className={styles.fileSummary}>
                  <strong>{item.file.name}</strong>
                  <span>{Math.max(1, Math.round(item.file.size / 1024))} KB</span>
                  {(item.status === "uploading" || item.status === "uploaded") && (
                    <progress
                      aria-label={`Upload progress for ${item.file.name}`}
                      aria-valuenow={item.progress}
                      value={item.progress}
                      max={100}
                    />
                  )}
                  {item.status === "uploaded" && <span className={styles.success}>Uploaded</span>}
                  {item.error && (
                    <span className={styles.error} role="alert">
                      {item.error}
                    </span>
                  )}
                </div>
                <div className={styles.queueActions}>
                  {item.document && (
                    <Link href={`/documents/${item.document.id}`}>
                      Open {item.file.name}
                    </Link>
                  )}
                  {item.status === "error" && !item.clientError && (
                    <button type="button" onClick={() => uploadItem(item)}>
                      Retry {item.file.name}
                    </button>
                  )}
                  {item.status !== "uploading" && (
                    <button
                      type="button"
                      className={styles.textButton}
                      onClick={() =>
                        setItems((current) =>
                          current.filter((candidate) => candidate.id !== item.id),
                        )
                      }
                    >
                      Remove {item.file.name}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}
