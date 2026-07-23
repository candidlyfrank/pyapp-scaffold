"use client";

import { useEffect, useRef } from "react";

import type { InteractionMessage, Model, ResponseMode } from "../types";
import styles from "../interactions.module.css";
import Composer from "./Composer";
import MessageBubble from "./MessageBubble";

type ConversationViewProps = {
  messages: InteractionMessage[];
  isLoading: boolean;
  draft: string;
  model: Model;
  mode: ResponseMode;
  onDraftChange: (value: string) => void;
  onModelChange: (value: Model) => void;
  onModeChange: (value: ResponseMode) => void;
  onSubmit: (value: string) => void;
  onRetry: (id: string) => void;
};

export default function ConversationView(props: ConversationViewProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [props.messages, props.isLoading]);

  return (
    <div className={styles.conversation}>
      <div className={styles.conversationHeader}>
        <span className={styles.conversationMark}>K</span>
        <span>Kimi</span>
      </div>
      <div className={styles.messageLog} role="log" aria-label="Conversation" aria-live="polite">
        <div className={styles.messageColumn}>
          {props.messages.map((message) => (
            <MessageBubble key={message.id} message={message} onRetry={props.onRetry} />
          ))}
          {props.isLoading && (
            <div className={styles.typing} role="status">
              <span className={styles.assistantAvatar} aria-hidden="true">K</span>
              <span>Kimi is thinking</span>
              <span className={styles.typingDots} aria-hidden="true"><i /><i /><i /></span>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>
      <div className={styles.conversationComposer}>
        <Composer
          compact
          value={props.draft}
          model={props.model}
          mode={props.mode}
          disabled={props.isLoading}
          onChange={props.onDraftChange}
          onModelChange={props.onModelChange}
          onModeChange={props.onModeChange}
          onSubmit={props.onSubmit}
        />
        <p className={styles.disclaimer}>Kimi can make mistakes. Check important information.</p>
      </div>
    </div>
  );
}
