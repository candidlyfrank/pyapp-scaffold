import type {
  DocumentErrorPayload,
  DocumentMetadataUpdate,
  DocumentQuery,
  DocumentRecord,
} from "../types";
import { readCookie } from "./csrf";

const COLLECTION_URL = "/api/documents/";

export class DocumentApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "DocumentApiError";
  }
}

async function parseError(response: Response): Promise<DocumentApiError> {
  try {
    const body = (await response.json()) as { error?: DocumentErrorPayload };
    if (body.error) {
      return new DocumentApiError(
        response.status,
        body.error.code,
        body.error.message,
        body.error.fields,
      );
    }
  } catch {
    // The fallback below intentionally hides non-JSON server details.
  }
  return new DocumentApiError(
    response.status,
    "request_failed",
    "The document service could not complete the request.",
  );
}

async function requireOk(response: Response): Promise<Response> {
  if (!response.ok) throw await parseError(response);
  return response;
}

async function csrfToken(): Promise<string> {
  let token = readCookie("csrftoken");
  if (!token) {
    await requireOk(
      await fetch(COLLECTION_URL, {
        credentials: "same-origin",
      }),
    );
    token = readCookie("csrftoken");
  }
  if (!token) {
    throw new DocumentApiError(
      403,
      "csrf_token_missing",
      "Refresh the page before changing documents.",
    );
  }
  return token;
}

export async function listDocuments(
  query: DocumentQuery = {},
): Promise<DocumentRecord[]> {
  const parameters = new URLSearchParams();
  if (query.q) parameters.set("q", query.q);
  if (query.contentType) parameters.set("content_type", query.contentType);
  if (query.tag) parameters.set("tag", query.tag);
  if (query.ordering) parameters.set("ordering", query.ordering);
  const suffix = parameters.size ? `?${parameters.toString()}` : "";
  const response = await requireOk(
    await fetch(`${COLLECTION_URL}${suffix}`, {
      credentials: "same-origin",
    }),
  );
  const body = (await response.json()) as { documents: DocumentRecord[] };
  return body.documents;
}

export async function getDocument(id: string): Promise<DocumentRecord> {
  const response = await requireOk(
    await fetch(`${COLLECTION_URL}${encodeURIComponent(id)}/`, {
      credentials: "same-origin",
    }),
  );
  return (await response.json()) as DocumentRecord;
}

export async function updateDocument(
  id: string,
  metadata: DocumentMetadataUpdate,
): Promise<DocumentRecord> {
  const token = await csrfToken();
  const response = await requireOk(
    await fetch(`${COLLECTION_URL}${encodeURIComponent(id)}/`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": token,
      },
      body: JSON.stringify(metadata),
    }),
  );
  return (await response.json()) as DocumentRecord;
}

export async function replaceDocument(
  id: string,
  metadata: DocumentMetadataUpdate,
  file: File,
): Promise<DocumentRecord> {
  const token = await csrfToken();
  const form = new FormData();
  form.append("metadata", JSON.stringify(metadata));
  form.append("file", file);
  const response = await requireOk(
    await fetch(`${COLLECTION_URL}${encodeURIComponent(id)}/`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "X-CSRFToken": token },
      body: form,
    }),
  );
  return (await response.json()) as DocumentRecord;
}

export async function deleteDocument(id: string): Promise<void> {
  const token = await csrfToken();
  await requireOk(
    await fetch(`${COLLECTION_URL}${encodeURIComponent(id)}/`, {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-CSRFToken": token },
    }),
  );
}

export async function uploadDocument(
  file: File,
  onProgress: (progress: number) => void,
): Promise<DocumentRecord> {
  const token = await csrfToken();
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", COLLECTION_URL);
    request.withCredentials = true;
    request.setRequestHeader("X-CSRFToken", token);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    request.onerror = () => {
      reject(
        new DocumentApiError(
          0,
          "network_error",
          "The document upload could not reach Django.",
        ),
      );
    };
    request.onload = () => {
      let body: {
        results?: Array<{ document?: DocumentRecord }>;
        error?: DocumentErrorPayload;
      };
      try {
        body = JSON.parse(request.responseText) as typeof body;
      } catch {
        reject(
          new DocumentApiError(
            request.status,
            "invalid_response",
            "Django returned an invalid upload response.",
          ),
        );
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(
          new DocumentApiError(
            request.status,
            body.error?.code ?? "upload_failed",
            body.error?.message ?? "The document could not be uploaded.",
            body.error?.fields,
          ),
        );
        return;
      }
      const document = body.results?.[0]?.document;
      if (!document) {
        reject(
          new DocumentApiError(
            request.status,
            "invalid_response",
            "Django did not return the uploaded document.",
          ),
        );
        return;
      }
      onProgress(100);
      resolve(document);
    };

    const form = new FormData();
    form.append("files", file);
    request.send(form);
  });
}
