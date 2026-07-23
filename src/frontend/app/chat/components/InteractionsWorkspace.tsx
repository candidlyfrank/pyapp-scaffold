"use client";

import { useEffect, useRef, useState } from "react";

import { PreferencesProvider, usePreferences } from "../context/PreferencesContext";
import { useInteractions } from "../hooks/useInteractions";
import styles from "../interactions.module.css";
import ConversationView from "./ConversationView";
import EmptyState from "./EmptyState";
import Icon from "./Icon";
import Sidebar from "./Sidebar";

function WorkspaceContent() {
  const preferences = usePreferences();
  const interactions = useInteractions(preferences.model, preferences.mode);
  const [draft, setDraft] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const openDrawerRef = useRef<HTMLButtonElement>(null);
  const closeDrawerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!drawerOpen) return;
    closeDrawerRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        drawerRef.current?.querySelectorAll<HTMLElement>("button, [href], input, [tabindex]:not([tabindex='-1'])") ?? [],
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  function closeDrawer() {
    openDrawerRef.current?.focus();
    setDrawerOpen(false);
  }

  function submit(content: string) {
    if (interactions.sendMessage(content)) setDraft("");
  }

  function newChat() {
    if (interactions.messages.length > 0 && !window.confirm("Start a new chat?")) return;
    interactions.newChat();
    setDraft("");
    if (drawerOpen) closeDrawer();
  }

  return (
    <div className={styles.workspace}>
      <Sidebar
        collapsed={preferences.sidebarCollapsed}
        onToggle={preferences.toggleSidebar}
        onNewChat={newChat}
        onSample={interactions.showSample}
      />
      <main className={styles.mainCanvas}>
        <header className={styles.mobileHeader}>
          <button ref={openDrawerRef} type="button" aria-label="Open navigation" onClick={() => setDrawerOpen(true)}>
            <Icon name="menu" />
          </button>
          <span className={styles.mobileBrand}>K</span>
          <button type="button" aria-label="New mobile chat" onClick={newChat}><Icon name="plus" /></button>
        </header>
        {interactions.messages.length === 0 ? (
          <EmptyState
            draft={draft}
            model={preferences.model}
            mode={preferences.mode}
            isLoading={interactions.isLoading}
            onDraftChange={setDraft}
            onModelChange={preferences.setModel}
            onModeChange={preferences.setMode}
            onSubmit={submit}
          />
        ) : (
          <ConversationView
            messages={interactions.messages}
            isLoading={interactions.isLoading}
            draft={draft}
            model={preferences.model}
            mode={preferences.mode}
            onDraftChange={setDraft}
            onModelChange={preferences.setModel}
            onModeChange={preferences.setMode}
            onSubmit={submit}
            onRetry={interactions.retryMessage}
          />
        )}
        <div className={styles.liveNotices} aria-live="polite">
          {interactions.error && <p role="alert">{interactions.error}</p>}
          {interactions.storageWarning && <p>{interactions.storageWarning}</p>}
        </div>
      </main>
      {drawerOpen && (
        <div className={styles.drawerLayer}>
          <button type="button" className={styles.drawerScrim} aria-label="Close navigation overlay" onClick={closeDrawer} />
          <div ref={drawerRef} className={styles.drawer} role="dialog" aria-modal="true" aria-label="Navigation">
            <button ref={closeDrawerRef} type="button" className={styles.drawerClose} aria-label="Close navigation" onClick={closeDrawer}>
              <Icon name="x" />
            </button>
            <Sidebar
              drawer
              collapsed={false}
              onToggle={() => undefined}
              onNewChat={newChat}
              onSample={(title) => { interactions.showSample(title); closeDrawer(); }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function InteractionsWorkspace() {
  return <PreferencesProvider><WorkspaceContent /></PreferencesProvider>;
}
