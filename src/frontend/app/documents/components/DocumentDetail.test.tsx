import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DocumentRecord } from "../types";
import DocumentDetail from "./DocumentDetail";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const documentFixture: DocumentRecord = {
  id: "b240929d-0967-407e-942e-22e78778a22b",
  filename: "notes.txt",
  title: "Knowledge notes",
  description: "RAG source",
  tags: ["rag"],
  contentType: "text/plain",
  size: 5,
  sha256: "a".repeat(64),
  createdAt: "2026-07-23T10:00:00Z",
  updatedAt: "2026-07-23T11:00:00Z",
  downloadUrl: "/api/documents/b240929d-0967-407e-942e-22e78778a22b/download/",
};

describe("DocumentDetail", () => {
  beforeEach(() => push.mockReset());

  it("loads metadata and saves editable fields", async () => {
    const saveDocument = vi.fn().mockResolvedValue({
      ...documentFixture,
      filename: "renamed.txt",
      title: "Updated knowledge",
      tags: ["cms", "rag"],
    });
    const user = userEvent.setup();
    render(
      <DocumentDetail
        documentId={documentFixture.id}
        loadDocument={vi.fn().mockResolvedValue(documentFixture)}
        saveDocument={saveDocument}
      />,
    );

    expect(await screen.findByDisplayValue("Knowledge notes")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Filename"));
    await user.type(screen.getByLabelText("Filename"), "renamed.txt");
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Updated knowledge");
    await user.clear(screen.getByLabelText("Tags"));
    await user.type(screen.getByLabelText("Tags"), "rag, cms");
    await user.click(screen.getByRole("button", { name: "Save metadata" }));

    expect(saveDocument).toHaveBeenCalledWith(documentFixture.id, {
      filename: "renamed.txt",
      title: "Updated knowledge",
      description: "RAG source",
      tags: ["rag", "cms"],
    });
    expect(await screen.findByText("Metadata saved.")).toBeInTheDocument();
    expect(screen.getByText("renamed.txt")).toBeInTheDocument();
  });

  it("preserves form values after a failed save", async () => {
    const user = userEvent.setup();
    render(
      <DocumentDetail
        documentId={documentFixture.id}
        loadDocument={vi.fn().mockResolvedValue(documentFixture)}
        saveDocument={vi.fn().mockRejectedValue(new Error("Save failed."))}
      />,
    );
    await screen.findByDisplayValue("Knowledge notes");
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Unsaved title");
    await user.click(screen.getByRole("button", { name: "Save metadata" }));

    expect(await screen.findByText("Save failed.")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("Unsaved title");
  });

  it("replaces the file with current metadata", async () => {
    const replaceFile = vi.fn().mockResolvedValue({
      ...documentFixture,
      filename: "replacement.md",
      contentType: "text/markdown",
    });
    const user = userEvent.setup();
    render(
      <DocumentDetail
        documentId={documentFixture.id}
        loadDocument={vi.fn().mockResolvedValue(documentFixture)}
        replaceFile={replaceFile}
      />,
    );
    await screen.findByDisplayValue("Knowledge notes");
    const replacement = new File(["# replacement"], "replacement.md");
    await user.upload(screen.getByLabelText("Replacement file"), replacement);
    await user.click(screen.getByRole("button", { name: "Replace file" }));

    expect(replaceFile).toHaveBeenCalledWith(
      documentFixture.id,
      expect.objectContaining({ title: "Knowledge notes" }),
      replacement,
    );
    expect(await screen.findByText("File replaced.")).toBeInTheDocument();
  });

  it("confirms deletion and returns to the library", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const removeDocument = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <DocumentDetail
        documentId={documentFixture.id}
        loadDocument={vi.fn().mockResolvedValue(documentFixture)}
        removeDocument={removeDocument}
      />,
    );
    await screen.findByDisplayValue("Knowledge notes");
    await user.click(screen.getByRole("button", { name: "Delete document" }));

    await waitFor(() => expect(removeDocument).toHaveBeenCalledWith(documentFixture.id));
    expect(window.confirm).toHaveBeenCalledWith(
      'Delete "Knowledge notes"? This cannot be undone.',
    );
    expect(push).toHaveBeenCalledWith("/documents");
  });
});
