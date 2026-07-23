import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Composer from "./Composer";

function renderComposer(overrides: Partial<React.ComponentProps<typeof Composer>> = {}) {
  const props: React.ComponentProps<typeof Composer> = {
    value: "",
    model: "K2.6",
    mode: "Standard",
    disabled: false,
    onChange: vi.fn(),
    onModelChange: vi.fn(),
    onModeChange: vi.fn(),
    onSubmit: vi.fn(),
    ...overrides,
  };
  return { ...render(<Composer {...props} />), props };
}

describe("Composer", () => {
  it("uses the exact placeholder and disables empty submission", () => {
    renderComposer();

    expect(
      screen.getByPlaceholderText("Ask anything, or task an agent..."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("submits trimmed content with Enter", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    renderComposer({ value: "  Hello  ", onSubmit });

    await user.click(screen.getByLabelText("Message"));
    await user.keyboard("{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("Hello");
  });

  it("keeps Shift+Enter available for newlines", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    renderComposer({ value: "Hello", onSubmit });

    await user.click(screen.getByLabelText("Message"));
    await user.keyboard("{Shift>}{Enter}{/Shift}");

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows and removes a selected file locally", async () => {
    const user = userEvent.setup();
    renderComposer();
    const file = new File(["notes"], "notes.txt", { type: "text/plain" });

    await user.upload(screen.getByLabelText("Attach files"), file);
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove notes.txt" }));
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });
});
