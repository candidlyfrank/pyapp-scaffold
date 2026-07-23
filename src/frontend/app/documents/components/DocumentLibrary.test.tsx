import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DocumentRecord } from "../types";
import DocumentLibrary from "./DocumentLibrary";

const documentFixture: DocumentRecord = {
  id: "b240929d-0967-407e-942e-22e78778a22b",
  filename: "quarterly-report.pdf",
  title: "Quarterly report",
  description: "Finance source",
  tags: ["finance"],
  contentType: "application/pdf",
  size: 2048,
  sha256: "a".repeat(64),
  createdAt: "2026-07-23T10:00:00Z",
  updatedAt: "2026-07-23T11:00:00Z",
  downloadUrl: "/api/documents/b240929d-0967-407e-942e-22e78778a22b/download/",
};

describe("DocumentLibrary", () => {
  it("renders live Django records with detail and download links", async () => {
    render(<DocumentLibrary loadDocuments={vi.fn().mockResolvedValue([documentFixture])} />);

    expect(screen.getByText("Loading documents…")).toBeInTheDocument();
    expect(
      await screen.findByRole("link", { name: "Quarterly report" }),
    ).toHaveAttribute("href", `/documents/${documentFixture.id}`);
    expect(
      screen.getByRole("link", { name: "Download Quarterly report" }),
    ).toHaveAttribute("href", documentFixture.downloadUrl);
    expect(screen.getByText("2 KB")).toBeInTheDocument();
  });

  it("shows an empty library state", async () => {
    render(<DocumentLibrary loadDocuments={vi.fn().mockResolvedValue([])} />);

    expect(await screen.findByText("Your document library is empty.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upload your first document" })).toHaveAttribute(
      "href",
      "/documents/upload",
    );
  });

  it("sends search, type, tag, and ordering controls to Django", async () => {
    const loadDocuments = vi.fn().mockResolvedValue([documentFixture]);
    const user = userEvent.setup();
    render(<DocumentLibrary loadDocuments={loadDocuments} />);
    await screen.findByText("Quarterly report");

    await user.type(screen.getByRole("searchbox", { name: "Search documents" }), "report");
    await user.selectOptions(screen.getByLabelText("Document type"), "application/pdf");
    await user.type(screen.getByLabelText("Tag"), "finance");
    await user.selectOptions(screen.getByLabelText("Sort documents"), "-updated_at");

    await waitFor(() =>
      expect(loadDocuments).toHaveBeenLastCalledWith({
        q: "report",
        contentType: "application/pdf",
        tag: "finance",
        ordering: "-updated_at",
      }),
    );
  });

  it("shows an API error and allows retry", async () => {
    const loadDocuments = vi
      .fn()
      .mockRejectedValueOnce(new Error("Django is unavailable."))
      .mockResolvedValueOnce([documentFixture]);
    const user = userEvent.setup();
    render(<DocumentLibrary loadDocuments={loadDocuments} />);

    expect(await screen.findByText("Django is unavailable.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Quarterly report")).toBeInTheDocument();
  });
});
