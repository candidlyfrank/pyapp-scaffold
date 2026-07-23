import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RichText from "./RichText";

describe("RichText", () => {
  it("renders the supported rich text subset", () => {
    render(
      <RichText
        content={"## Heading\n\n- First\n- Second\n\nUse **care** and `code`.\n\n```ts\nconst x = 1;\n```"}
      />,
    );

    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("care").tagName).toBe("STRONG");
    expect(screen.getByText("code").tagName).toBe("CODE");
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });

  it("does not create raw HTML and blocks unsafe link protocols", () => {
    const { container } = render(
      <RichText content={'<script>alert(1)</script> [unsafe](javascript:alert(1)) [safe](https://example.com)'} />,
    );

    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
    expect(screen.getByText("unsafe").closest("a")).toBeNull();
    expect(screen.getByRole("link", { name: "safe" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
  });
});
