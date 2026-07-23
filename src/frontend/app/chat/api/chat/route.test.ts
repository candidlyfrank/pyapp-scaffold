import { describe, expect, it } from "vitest";

import { handleChat } from "./route";

function request(body: unknown, contentType = "application/json") {
  return new Request("http://localhost/interactions/api/chat", {
    method: "POST",
    headers: { "Content-Type": contentType },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

const noWait = async () => undefined;

describe("interactions chat route", () => {
  it("requires JSON", async () => {
    expect((await handleChat(request("x", "text/plain"), noWait)).status).toBe(415);
  });

  it("validates message, model, and mode", async () => {
    const invalidBodies = [
      { message: " ", model: "K2.6", mode: "Standard" },
      { message: "hello", model: "unknown", mode: "Standard" },
      { message: "hello", model: "K2.6", mode: "unknown" },
    ];

    for (const body of invalidBodies) {
      expect((await handleChat(request(body), noWait)).status).toBe(400);
    }
  });

  it("returns an original markdown response", async () => {
    const response = await handleChat(
      request({ message: "Plan a trip", model: "K2.6", mode: "Standard" }),
      noWait,
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toMatchObject({
      id: expect.any(String),
      content: expect.stringContaining("##"),
      createdAt: expect.any(String),
    });
  });
});
