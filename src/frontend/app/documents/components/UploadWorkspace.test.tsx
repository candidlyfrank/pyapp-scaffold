import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DocumentRecord } from "../types";
import UploadWorkspace from "./UploadWorkspace";

const uploadedDocument: DocumentRecord = {
  id: "b240929d-0967-407e-942e-22e78778a22b",
  filename: "notes.txt",
  title: "notes",
  description: "",
  tags: [],
  contentType: "text/plain",
  size: 5,
  sha256: "a".repeat(64),
  contentRevision: 1,
  createdAt: "2026-07-23T10:00:00Z",
  updatedAt: "2026-07-23T10:00:00Z",
  downloadUrl: "/api/documents/b240929d-0967-407e-942e-22e78778a22b/download/",
};

describe("UploadWorkspace", () => {
  it("uploads valid files independently and shows progress", async () => {
    const uploadFile = vi.fn(
      async (file: File, onProgress: (value: number) => void) => {
        onProgress(50);
        return { ...uploadedDocument, filename: file.name };
      },
    );
    const user = userEvent.setup();
    render(<UploadWorkspace uploadFile={uploadFile} />);

    await user.upload(
      screen.getByLabelText("Choose documents"),
      new File(["hello"], "notes.txt", { type: "text/plain" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload all" }));

    expect(await screen.findByText("Uploaded")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("link", { name: "Open notes.txt" }),
    ).toHaveAttribute("href", `/documents/${uploadedDocument.id}`);
  });

  it("adds files dropped onto the workspace", () => {
    render(<UploadWorkspace uploadFile={vi.fn()} />);
    const file = new File(["name,value"], "data.csv", { type: "text/csv" });

    fireEvent.drop(screen.getByTestId("document-dropzone"), {
      dataTransfer: { files: [file] },
    });

    expect(screen.getByText("data.csv")).toBeInTheDocument();
  });

  it("shows client feedback for unsupported and oversized files", () => {
    render(<UploadWorkspace uploadFile={vi.fn()} />);
    const input = screen.getByLabelText("Choose documents");

    fireEvent.change(input, {
      target: { files: [new File(["bad"], "tool.exe")] },
    });
    expect(screen.getByText("This file type is not supported.")).toBeInTheDocument();

    const oversized = new File(["x"], "large.pdf");
    Object.defineProperty(oversized, "size", { value: 25 * 1024 * 1024 + 1 });
    fireEvent.change(input, { target: { files: [oversized] } });
    expect(screen.getByText("This file is larger than 25 MB.")).toBeInTheDocument();
  });

  it("keeps successful uploads when another fails and supports retry", async () => {
    const uploadFile = vi
      .fn()
      .mockResolvedValueOnce(uploadedDocument)
      .mockRejectedValueOnce(new Error("Django rejected this file."))
      .mockResolvedValueOnce({ ...uploadedDocument, filename: "two.txt" });
    const user = userEvent.setup();
    render(<UploadWorkspace uploadFile={uploadFile} />);

    await user.upload(screen.getByLabelText("Choose documents"), [
      new File(["one"], "one.txt"),
      new File(["two"], "two.txt"),
    ]);
    await user.click(screen.getByRole("button", { name: "Upload all" }));

    expect(await screen.findByText("Django rejected this file.")).toBeInTheDocument();
    expect(screen.getByText("Uploaded")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry two.txt" }));

    await waitFor(() => expect(uploadFile).toHaveBeenCalledTimes(3));
    expect(screen.getAllByText("Uploaded")).toHaveLength(2);
  });

  it("shows the unauthenticated local-development warning", () => {
    render(<UploadWorkspace uploadFile={vi.fn()} />);

    expect(
      screen.getByText(/uploads are currently unauthenticated/i),
    ).toBeInTheDocument();
  });
});
