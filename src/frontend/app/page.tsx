import Link from "next/link";

export default function Home() {
  return (
    <main>
      <p className="eyebrow">PyApp Scaffold</p>
      <h1>Next.js, Django, and Caddy on one origin.</h1>
      <p>
        Next.js renders the frontend while Django remains responsible for API requests,
        sessions, permissions, and CSRF validation.
      </p>
      <Link href="/account">View the authenticated request example →</Link>
      <p>
        <Link href="/chat">Open the Django-backed chat →</Link>
      </p>
      <p>
        <Link href="/documents/upload">Upload documents →</Link>
      </p>
      <p>
        <Link href="/documents">Open the document library →</Link>
      </p>
    </main>
  );
}
