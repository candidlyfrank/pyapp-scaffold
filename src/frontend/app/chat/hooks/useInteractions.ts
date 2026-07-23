"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { loadMessages, saveMessages } from "../lib/storage";
import {
  MAX_MESSAGE_LENGTH,
  type ChatResponse,
  type InteractionMessage,
  type Model,
  type ResponseMode,
} from "../types";

const GENERIC_ERROR = "That response could not be completed. Check your connection and try again.";

function isChatResponse(value: unknown): value is ChatResponse {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.content === "string" &&
    typeof item.createdAt === "string" &&
    Number.isFinite(Date.parse(item.createdAt))
  );
}

export function useInteractions(model: Model, mode: ResponseMode) {
  const [messages, setMessages] = useState<InteractionMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const inFlight = useRef(false);
  const abortController = useRef<AbortController | null>(null);
  const persistHistory = useRef(true);

  useEffect(() => {
    setMessages((current) => current.length > 0 ? current : loadMessages());
    setHydrated(true);
    return () => abortController.current?.abort();
  }, []);

  useEffect(() => {
    if (!hydrated || !persistHistory.current) return;
    setStorageWarning(saveMessages(messages) ? null : "History is available for this tab only.");
  }, [hydrated, messages]);

  const runRequest = useCallback(async (id: string, content: string) => {
    abortController.current = new AbortController();
    try {
      const response = await fetch("/interactions/api/chat", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, model, mode }),
        signal: abortController.current.signal,
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok || !isChatResponse(payload)) throw new Error("Invalid response");

      setMessages((current) => [
        ...current.map((message) => message.id === id ? { ...message, status: "sent" as const } : message),
        { ...payload, role: "assistant", status: "sent" },
      ]);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      setMessages((current) => current.map((message) =>
        message.id === id ? { ...message, status: "failed" as const } : message,
      ));
      setError(GENERIC_ERROR);
    } finally {
      inFlight.current = false;
      setIsLoading(false);
      abortController.current = null;
    }
  }, [model, mode]);

  const sendMessage = useCallback((raw: string) => {
    const content = raw.trim();
    if (inFlight.current || !content || content.length > MAX_MESSAGE_LENGTH) return false;

    const id = crypto.randomUUID();
    inFlight.current = true;
    persistHistory.current = true;
    setError(null);
    setIsLoading(true);
    setMessages((current) => [...current, {
      id,
      role: "user",
      content,
      createdAt: new Date().toISOString(),
      status: "pending",
    }]);
    void runRequest(id, content);
    return true;
  }, [runRequest]);

  const retryMessage = useCallback((id: string) => {
    if (inFlight.current) return;
    const target = messages.find((message) => message.id === id && message.status === "failed");
    if (!target) return;

    inFlight.current = true;
    persistHistory.current = true;
    setError(null);
    setIsLoading(true);
    setMessages((current) => current.map((message) =>
      message.id === id ? { ...message, status: "pending" as const } : message,
    ));
    void runRequest(id, target.content);
  }, [messages, runRequest]);

  const newChat = useCallback(() => {
    abortController.current?.abort();
    inFlight.current = false;
    persistHistory.current = true;
    setIsLoading(false);
    setError(null);
    setMessages([]);
  }, []);

  const showSample = useCallback((title: string) => {
    persistHistory.current = false;
    setError(null);
    setMessages([
      {
        id: `sample-user-${title}`,
        role: "user",
        content: title,
        createdAt: "2026-07-20T09:00:00.000Z",
        status: "sent",
      },
      {
        id: `sample-assistant-${title}`,
        role: "assistant",
        content: "## Saved inspiration\n\nThis sample shows how a previous conversation can appear in the workspace without changing your active local history.",
        createdAt: "2026-07-20T09:00:01.000Z",
        status: "sent",
      },
    ]);
  }, []);

  return { messages, isLoading, error, storageWarning, sendMessage, retryMessage, newChat, showSample };
}
