import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DropdownMenu from "./DropdownMenu";

describe("DropdownMenu", () => {
  it("supports keyboard selection", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <DropdownMenu
        label="Choose model"
        value="K2.6"
        options={["K2.6", "Gemini 2.5 Pro"]}
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Choose model" }));
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenCalledWith("Gemini 2.5 Pro");
  });

  it("closes with Escape and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(
      <DropdownMenu
        label="Choose mode"
        value="Standard"
        options={["Standard", "Thinking"]}
        onChange={() => undefined}
      />,
    );
    const trigger = screen.getByRole("button", { name: "Choose mode" });

    await user.click(trigger);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
