import { describe, expect, it } from "vitest";

import { loadMessages, loadPreferences, saveMessages, savePreferences } from "./storage";

const userMessage = {
  id: "u-1",
  role: "user" as const,
  content: "Hello",
  createdAt: "2026-07-21T12:00:00.000Z",
  status: "sent" as const,
};

function memoryStorage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));

  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  };
}

describe("interaction storage", () => {
  it("round trips validated messages", () => {
    const storage = memoryStorage();

    expect(saveMessages([userMessage], storage)).toBe(true);
    expect(loadMessages(storage)).toEqual([userMessage]);
  });

  it("normalizes interrupted pending messages to failed", () => {
    const storage = memoryStorage({
      "kimi.interactions.messages.v1": JSON.stringify({
        version: 1,
        messages: [{ ...userMessage, status: "pending" }],
      }),
    });

    expect(loadMessages(storage)[0].status).toBe("failed");
  });

  it("rejects malformed records and unsupported versions", () => {
    expect(
      loadMessages(memoryStorage({ "kimi.interactions.messages.v1": "{" })),
    ).toEqual([]);
    expect(
      loadPreferences(
        memoryStorage({
          "kimi.interactions.preferences.v1": JSON.stringify({ version: 2 }),
        }),
      ),
    ).toEqual({ sidebarCollapsed: false, model: "K2.6", mode: "Standard" });
  });

  it("round trips supported preferences and survives write failure", () => {
    const storage = memoryStorage();
    const preferences = {
      sidebarCollapsed: true,
      model: "Gemini 2.5 Pro" as const,
      mode: "Thinking" as const,
    };

    expect(savePreferences(preferences, storage)).toBe(true);
    expect(loadPreferences(storage)).toEqual(preferences);
    expect(
      saveMessages([userMessage], {
        setItem: () => {
          throw new Error("quota");
        },
      }),
    ).toBe(false);
  });
});
