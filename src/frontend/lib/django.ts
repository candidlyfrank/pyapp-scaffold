import "server-only";

import { cookies } from "next/headers";

const REQUEST_TIMEOUT_MS = 5_000;

export class DjangoRequestError extends Error {
  constructor(public readonly status: number) {
    super(`Django request failed with status ${status}`);
    this.name = "DjangoRequestError";
  }
}

export async function djangoServerFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new TypeError("Django request path must be relative to the configured origin");
  }

  const origin = process.env.DJANGO_INTERNAL_URL;
  if (!origin) {
    throw new Error("Django is not configured for server-side requests");
  }

  const cookieStore = await cookies();
  const headers = new Headers(init.headers);
  headers.set("Cookie", cookieStore.toString());

  const response = await fetch(new URL(path, origin), {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new DjangoRequestError(response.status);
  }
  return response;
}
