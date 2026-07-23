import type { InteractionMessage } from "../types";
import styles from "../interactions.module.css";
import Icon from "./Icon";
import RichText from "./RichText";

export default function MessageBubble({
  message,
  onRetry,
}: {
  message: InteractionMessage;
  onRetry: (id: string) => void;
}) {
  const user = message.role === "user";
  return (
    <article className={`${styles.messageRow} ${user ? styles.userRow : styles.assistantRow}`}>
      {!user && <div className={styles.assistantAvatar} aria-hidden="true">K</div>}
      <div className={`${styles.messageBubble} ${user ? styles.userBubble : styles.assistantBubble}`}>
        {user ? <p>{message.content}</p> : <RichText content={message.content} />}
        {message.status === "pending" && <span className={styles.delivery}>Sending…</span>}
        {message.status === "failed" && (
          <div className={styles.failedMessage}>
            <span>Not sent</span>
            <button type="button" onClick={() => onRetry(message.id)} aria-label="Retry message">
              Try again
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
