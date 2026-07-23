import DocumentLibrary from "./components/DocumentLibrary";
import DocumentsNav from "./components/DocumentsNav";
import styles from "./documents.module.css";

export default function DocumentsPage() {
  return (
    <div className={styles.documentApp}>
      <DocumentsNav />
      <main className={styles.documentMain}>
        <DocumentLibrary />
      </main>
    </div>
  );
}
