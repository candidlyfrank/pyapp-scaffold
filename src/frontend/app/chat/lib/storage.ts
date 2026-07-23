import {
  DEFAULT_PREFERENCES,
  MAX_MESSAGE_LENGTH,
  MODELS,
  RESPONSE_MODES,
  type InteractionMessage,
  type InteractionPreferences,
} from "../types";

export const MESSAGE_STORAGE_KEY = "kimi.interactions.messages.v1";
export const PREFERENCES_STORAGE_KEY = "kimi.interactions.preferences.v1";
const STORAGE_VERSION = 1;

type ReadStorage = Pick<Storage, "getItem">;
type WriteStorage = Pick<Storage, "setItem">;

function browserStorage(): Storage | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}

function isMessage(value: unknown): value is InteractionMessage {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;

  return (
    typeof item.id === "string" &&
    item.id.length > 0 &&
    (item.role === "user" || item.role === "assistant") &&
    typeof item.content === "string" &&
    item.content.trim().length > 0 &&
    item.content.length <= MAX_MESSAGE_LENGTH &&
    typeof item.createdAt === "string" &&
    Number.isFinite(Date.parse(item.createdAt)) &&
    (item.status === "pending" || item.status === "sent" || item.status === "failed") &&
    (item.role === "user" || item.status === "sent")
  );
}

function isPreferences(value: unknown): value is InteractionPreferences {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;

  return (
    typeof item.sidebarCollapsed === "boolean" &&
    MODELS.includes(item.model as InteractionPreferences["model"]) &&
    RESPONSE_MODES.includes(item.mode as InteractionPreferences["mode"])
  );
}

export function loadMessages(storage: ReadStorage | undefined = browserStorage()) {
  if (!storage) return [];

  try {
    const raw = storage.getItem(MESSAGE_STORAGE_KEY);
    if (!raw) return [];
    const payload = JSON.parse(raw) as { version?: unknown; messages?: unknown };
    if (payload.version !== STORAGE_VERSION || !Array.isArray(payload.messages)) return [];

    return payload.messages.filter(isMessage).map((message) =>
      message.status === "pending"
        ? { ...message, status: "failed" as const }
        : message,
    );
  } catch {
    return [];
  }
}

export function saveMessages(
  messages: InteractionMessage[],
  storage: WriteStorage | undefined = browserStorage(),
) {
  if (!storage) return false;
  try {
    storage.setItem(MESSAGE_STORAGE_KEY, JSON.stringify({ version: STORAGE_VERSION, messages }));
    return true;
  } catch {
    return false;
  }
}

export function loadPreferences(
  storage: ReadStorage | undefined = browserStorage(),
): InteractionPreferences {
  if (!storage) return DEFAULT_PREFERENCES;
  try {
    const raw = storage.getItem(PREFERENCES_STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    const payload = JSON.parse(raw) as { version?: unknown; preferences?: unknown };
    return payload.version === STORAGE_VERSION && isPreferences(payload.preferences)
      ? payload.preferences
      : DEFAULT_PREFERENCES;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function savePreferences(
  preferences: InteractionPreferences,
  storage: WriteStorage | undefined = browserStorage(),
) {
  if (!storage) return false;
  try {
    storage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ version: STORAGE_VERSION, preferences }),
    );
    return true;
  } catch {
    return false;
  }
}
