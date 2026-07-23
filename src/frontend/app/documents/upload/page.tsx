import DocumentsNav from "../components/DocumentsNav";
import UploadWorkspace from "../components/UploadWorkspace";
import styles from "../documents.module.css";

export default function DocumentUploadPage() {
  return (
    <div className={styles.documentApp}>
      <DocumentsNav />
      <main className={styles.documentMain}>
        <UploadWorkspace />
      </main>
    </div>
  );
}
