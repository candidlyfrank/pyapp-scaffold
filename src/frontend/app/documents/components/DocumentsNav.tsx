import Link from "next/link";

import styles from "../documents.module.css";

export default function DocumentsNav() {
  return (
    <nav aria-label="Document workspace" className={styles.nav}>
      <Link href="/" className={styles.brand}>
        PyApp
      </Link>
      <div className={styles.navLinks}>
        <Link href="/documents">Library</Link>
        <Link href="/documents/upload">Upload</Link>
      </div>
    </nav>
  );
}
