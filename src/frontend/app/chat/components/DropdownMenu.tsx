"use client";

import { useEffect, useId, useRef, useState } from "react";

import styles from "../interactions.module.css";
import Icon, { type IconName } from "./Icon";

type DropdownMenuProps<T extends string> = {
  label: string;
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
  align?: "left" | "right";
  icon?: IconName;
  iconOnly?: boolean;
};

export default function DropdownMenu<T extends string>({
  label,
  value,
  options,
  onChange,
  align = "left",
  icon,
  iconOnly = false,
}: DropdownMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (open) itemRefs.current[activeIndex]?.focus();
  }, [activeIndex, open]);

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  function closeAndRestore() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function select(option: T) {
    onChange(option);
    closeAndRestore();
  }

  function onMenuKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeAndRestore();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % options.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => (current - 1 + options.length) % options.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(options.length - 1);
    }
  }

  return (
    <div className={styles.dropdown} ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.dropdownTrigger}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => {
          setActiveIndex(Math.max(0, options.indexOf(value)));
          setOpen((current) => !current);
        }}
      >
        {icon && <Icon name={icon} />}
        {!iconOnly && <span>{value}</span>}
        {!iconOnly && <Icon name="chevron-down" width="15" height="15" />}
      </button>
      {open && (
        <div
          id={id}
          role="menu"
          className={`${styles.dropdownMenu} ${align === "right" ? styles.dropdownRight : ""}`}
          onKeyDown={onMenuKeyDown}
        >
          {options.map((option, index) => (
            <button
              key={option}
              ref={(node) => { itemRefs.current[index] = node; }}
              type="button"
              role="menuitem"
              className={option === value ? styles.selectedMenuItem : undefined}
              onClick={() => select(option)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  select(option);
                }
              }}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
