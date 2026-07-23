import DocumentDetail from "../components/DocumentDetail";
import DocumentsNav from "../components/DocumentsNav";
import styles from "../documents.module.css";

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className={styles.documentApp}>
      <DocumentsNav />
      <main className={styles.documentMain}>
        <DocumentDetail documentId={id} />
      </main>
    </div>
  );
}
