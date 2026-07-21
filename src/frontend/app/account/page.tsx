import Link from "next/link";

import { DjangoRequestError, djangoServerFetch } from "@/lib/django";

import MutationForm from "./mutation-form";

type Session = {
  authenticated: boolean;
  username: string | null;
};

export const dynamic = "force-dynamic";

export default async function AccountPage() {
  let session: Session | null = null;
  let unavailable = false;

  try {
    const response = await djangoServerFetch("/api/session/");
    session = (await response.json()) as Session;
  } catch (error) {
    if (!(error instanceof DjangoRequestError && error.status === 401)) {
      unavailable = true;
    }
  }

  return (
    <main>
      <p className="eyebrow">Authenticated SSR example</p>
      <h1>Account</h1>
      {unavailable ? (
        <p>The account service is temporarily unavailable. Please try again.</p>
      ) : session?.authenticated ? (
        <>
          <p>Signed in as {session.username}.</p>
          <MutationForm />
        </>
      ) : (
        <p>You are not signed in. Authenticate through the Django admin or login endpoint.</p>
      )}
      <p>
        <Link href="/">← Back home</Link>
      </p>
    </main>
  );
}
