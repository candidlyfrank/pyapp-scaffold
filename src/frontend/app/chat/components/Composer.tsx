"use client";

import { useEffect, useRef, useState } from "react";

import { MAX_MESSAGE_LENGTH, MODELS, RESPONSE_MODES, type Model, type ResponseMode } from "../types";
import styles from "../interactions.module.css";
import DropdownMenu from "./DropdownMenu";
import Icon from "./Icon";

type ComposerProps = {
  value: string;
  model: Model;
  mode: ResponseMode;
  disabled: boolean;
  onChange: (value: string) => void;
  onModelChange: (value: Model) => void;
  onModeChange: (value: ResponseMode) => void;
  onSubmit: (value: string) => void;
  compact?: boolean;
};

export default function Composer({
  value,
  model,
  mode,
  disabled,
  onChange,
  onModelChange,
  onModeChange,
  onSubmit,
  compact = false,
}: ComposerProps) {
  const [attachment, setAttachment] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const canSubmit = value.trim().length > 0 && value.trim().length <= MAX_MESSAGE_LENGTH && !disabled;

  useEffect(() => {
    if (!attachment?.type.startsWith("image/") || typeof URL.createObjectURL !== "function") {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(attachment);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [attachment]);

  function submit() {
    if (canSubmit) onSubmit(value.trim());
  }

  return (
    <div className={`${styles.composer} ${compact ? styles.compactComposer : ""}`}>
      {attachment && (
        <div className={styles.attachmentPreview}>
          {previewUrl ? <img src={previewUrl} alt="" /> : <Icon name="document" />}
          <span>{attachment.name}</span>
          <button type="button" aria-label={`Remove ${attachment.name}`} onClick={() => setAttachment(null)}>
            <Icon name="x" width="15" height="15" />
          </button>
        </div>
      )}
      <label className={styles.srOnly} htmlFor="interactions-message">Message</label>
      <textarea
        id="interactions-message"
        value={value}
        disabled={disabled}
        maxLength={MAX_MESSAGE_LENGTH}
        placeholder="Ask anything, or task an agent..."
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <div className={styles.composerToolbar}>
        <div className={styles.composerStart}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Choose attachment"
            onClick={() => inputRef.current?.click()}
          >
            <Icon name="plus" />
          </button>
          <input
            ref={inputRef}
            className={styles.srOnly}
            type="file"
            aria-label="Attach files"
            accept="image/*,.pdf,.txt,.md,.doc,.docx"
            onChange={(event) => setAttachment(event.target.files?.[0] ?? null)}
          />
        </div>
        <div className={styles.composerEnd}>
          <DropdownMenu label="Choose model" value={model} options={MODELS} onChange={onModelChange} align="right" />
          <DropdownMenu label="Choose response mode" value={mode} options={RESPONSE_MODES} onChange={onModeChange} align="right" />
          <button type="button" className={styles.sendButton} aria-label="Send message" disabled={!canSubmit} onClick={submit}>
            <Icon name="arrow-up" />
          </button>
        </div>
      </div>
    </div>
  );
}
