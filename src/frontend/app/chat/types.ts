export const MODELS = ["K2.6", "Gemini 2.5 Pro"] as const;
export const RESPONSE_MODES = ["Standard", "Thinking"] as const;
export const MAX_MESSAGE_LENGTH = 4_000;

export type Model = (typeof MODELS)[number];
export type ResponseMode = (typeof RESPONSE_MODES)[number];
export type MessageRole = "user" | "assistant";
export type MessageStatus = "pending" | "sent" | "failed";

export type InteractionMessage = {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status: MessageStatus;
};

export type InteractionPreferences = {
  sidebarCollapsed: boolean;
  model: Model;
  mode: ResponseMode;
};

export const DEFAULT_PREFERENCES: InteractionPreferences = {
  sidebarCollapsed: false,
  model: "K2.6",
  mode: "Standard",
};

export type ChatResponse = {
  id: string;
  content: string;
  createdAt: string;
};
