"use client";

import { useState } from "react";

function readCookie(name: string): string | undefined {
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : undefined;
}

export default function MutationForm() {
  const [message, setMessage] = useState("");

  async function submit() {
    const csrfToken = readCookie("csrftoken");
    if (!csrfToken) {
      setMessage("A CSRF cookie is required. Refresh the page and try again.");
      return;
    }

    const response = await fetch("/api/example-mutation/", {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      credentials: "same-origin",
    });
    setMessage(response.ok ? "Mutation accepted by Django." : "Django rejected the mutation.");
  }

  return (
    <section>
      <button type="button" onClick={submit}>
        Send CSRF-protected mutation
      </button>
      <p aria-live="polite">{message}</p>
    </section>
  );
}
