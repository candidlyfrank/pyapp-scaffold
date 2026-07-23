import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DocumentApiError,
  listDocuments,
  updateDocument,
  uploadDocument,
} from "./api";

const documentFixture = {
  id: "b240929d-0967-407e-942e-22e78778a22b",
  filename: "report.pdf",
  title: "Quarterly report",
  description: "",
  tags: ["finance"],
  contentType: "application/pdf",
  size: 128,
  sha256: "a".repeat(64),
  createdAt: "2026-07-23T10:00:00Z",
  updatedAt: "2026-07-23T10:00:00Z",
  downloadUrl: "/api/documents/b240929d-0967-407e-942e-22e78778a22b/download/",
};

describe("document API", () => {
  beforeEach(() => {
    document.cookie = "csrftoken=; Max-Age=0; path=/";
  });

  it("encodes list query parameters", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ documents: [documentFixture] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const documents = await listDocuments({
      q: "quarterly report",
      contentType: "application/pdf",
      tag: "finance",
      ordering: "-updated_at",
    });

    expect(documents).toEqual([documentFixture]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/documents/?q=quarterly+report&content_type=application%2Fpdf&tag=finance&ordering=-updated_at",
      { credentials: "same-origin" },
    );
  });

  it("sends a CSRF-protected metadata patch", async () => {
    document.cookie = "csrftoken=token-123; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(documentFixture), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await updateDocument("doc-id", { title: "New title" });

    expect(fetch).toHaveBeenCalledWith(
      "/api/documents/doc-id/",
      expect.objectContaining({
        method: "PATCH",
        credentials: "same-origin",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-CSRFToken": "token-123",
        }),
        body: JSON.stringify({ title: "New title" }),
      }),
    );
  });

  it("converts structured failures to DocumentApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "document_not_found",
              message: "Missing.",
              fields: {},
            },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(listDocuments()).rejects.toMatchObject({
      status: 404,
      code: "document_not_found",
      message: "Missing.",
    } satisfies Partial<DocumentApiError>);
  });

  it("reports XHR upload progress and returns the created document", async () => {
    document.cookie = "csrftoken=upload-token; path=/";
    let requestBody: FormData | undefined;
    let csrfHeader = "";

    class FakeXMLHttpRequest {
      status = 201;
      responseText = JSON.stringify({
        results: [{ status: "uploaded", document: documentFixture }],
      });
      upload = {
        onprogress: null as ((event: ProgressEvent) => void) | null,
      };
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;

      open() {}

      setRequestHeader(name: string, value: string) {
        if (name === "X-CSRFToken") csrfHeader = value;
      }

      send(body: FormData) {
        requestBody = body;
        this.upload.onprogress?.({
          lengthComputable: true,
          loaded: 5,
          total: 10,
        } as ProgressEvent);
        this.onload?.();
      }
    }

    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const onProgress = vi.fn();
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });

    const result = await uploadDocument(file, onProgress);

    expect(result).toEqual(documentFixture);
    expect(onProgress).toHaveBeenCalledWith(50);
    expect(csrfHeader).toBe("upload-token");
    expect(requestBody?.get("files")).toBe(file);
  });
});
