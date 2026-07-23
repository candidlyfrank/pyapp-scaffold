import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InteractionsWorkspace from "./InteractionsWorkspace";

function response(content = "## Mock answer") {
  return new Response(
    JSON.stringify({ id: "a-1", content, createdAt: "2026-07-21T12:00:01.000Z" }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

describe("InteractionsWorkspace", () => {
  beforeEach(() => {
    localStorage.clear();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("renders the complete Kimi-style empty shell", () => {
    render(<InteractionsWorkspace />);

    expect(screen.getByRole("heading", { name: "KIMI" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask anything, or task an agent...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New Chat" })).toBeInTheDocument();
    for (const label of ["Swarm", "Slides", "Deep Research", "Websites", "Docs", "Sheets"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText("Explore inspiration")).toBeInTheDocument();
  });

  it("collapses and expands the desktop sidebar", async () => {
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Expand sidebar" }));
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toBeInTheDocument();
  });

  it("inserts a capability prompt and sends with typing feedback", async () => {
    let resolveResponse!: (value: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { resolveResponse = resolve; })));
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.click(screen.getByRole("button", { name: "Websites" }));
    expect(screen.getByLabelText("Message")).toHaveValue("Design a polished website for a creative studio");
    await user.keyboard("{Enter}");

    expect(screen.getByText("Design a polished website for a creative studio")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Kimi is thinking");

    await act(async () => resolveResponse(response()));
    expect(await screen.findByRole("heading", { name: "Mock answer" })).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/interactions/api/chat",
      expect.objectContaining({
        body: JSON.stringify({
          message: "Design a polished website for a creative studio",
          model: "K2.6",
          mode: "Standard",
        }),
      }),
    );
  });

  it("retries a failed message in place", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(response()),
    );
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.type(screen.getByLabelText("Message"), "Hello{Enter}");
    await user.click(await screen.findByRole("button", { name: "Retry message" }));

    expect(await screen.findByRole("heading", { name: "Mock answer" })).toBeInTheDocument();
    expect(screen.getAllByText("Hello")).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("persists model and mode choices", async () => {
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.click(screen.getByRole("button", { name: "Choose model" }));
    await user.click(screen.getByRole("menuitem", { name: "Gemini 2.5 Pro" }));
    await user.click(screen.getByRole("button", { name: "Choose response mode" }));
    await user.click(screen.getByRole("menuitem", { name: "Thinking" }));

    expect(localStorage.getItem("kimi.interactions.preferences.v1")).toContain("Gemini 2.5 Pro");
    expect(localStorage.getItem("kimi.interactions.preferences.v1")).toContain("Thinking");
  });

  it("opens and closes the mobile navigation dialog", async () => {
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    const dialog = screen.getByRole("dialog", { name: "Navigation" });
    expect(dialog).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Close navigation" }));
    expect(screen.queryByRole("dialog", { name: "Navigation" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveFocus();
  });

  it("opens help and settings utility menus", async () => {
    const user = userEvent.setup();
    render(<InteractionsWorkspace />);

    await user.click(screen.getByRole("button", { name: "Help" }));
    expect(screen.getByRole("menuitem", { name: "Keyboard shortcuts" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Settings" }));
    expect(screen.getByRole("menuitem", { name: "Privacy" })).toBeInTheDocument();
  });
});
