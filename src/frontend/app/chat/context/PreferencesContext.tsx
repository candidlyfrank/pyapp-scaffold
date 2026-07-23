"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { loadPreferences, savePreferences } from "../lib/storage";
import {
  DEFAULT_PREFERENCES,
  type InteractionPreferences,
  type Model,
  type ResponseMode,
} from "../types";

type PreferencesContextValue = InteractionPreferences & {
  setModel: (model: Model) => void;
  setMode: (mode: ResponseMode) => void;
  toggleSidebar: () => void;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setPreferences(loadPreferences());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) savePreferences(preferences);
  }, [hydrated, preferences]);

  const value = useMemo<PreferencesContextValue>(() => ({
    ...preferences,
    setModel: (model) => setPreferences((current) => ({ ...current, model })),
    setMode: (mode) => setPreferences((current) => ({ ...current, mode })),
    toggleSidebar: () => setPreferences((current) => ({
      ...current,
      sidebarCollapsed: !current.sidebarCollapsed,
    })),
  }), [preferences]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error("usePreferences must be used inside PreferencesProvider");
  return context;
}
