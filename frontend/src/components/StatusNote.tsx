import styles from "./StatusNote.module.css";

interface StatusNoteProps {
  tone: "loading" | "error";
  /** Overrides the default per-tone message. */
  message?: string;
  /** Shows a retry button when provided (usually alongside `tone: "error"`). */
  onRetry?: () => void;
}

/** Inline loading/error note with an optional retry action. */
export function StatusNote({ tone, message, onRetry }: StatusNoteProps) {
  return (
    <div className={styles.note}>
      <span className={tone === "error" ? styles.errorText : styles.text}>
        {message ?? (tone === "loading" ? "Loading\u2026" : "Something went wrong")}
      </span>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
