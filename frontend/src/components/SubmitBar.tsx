import styles from "./SubmitBar.module.css";

interface SubmitBarProps {
  draftsCount: number;
  cancelCount: number;
  /** After the daily submission the set is locked until the next day. */
  locked: boolean;
  /** True while the submission request is in flight. */
  submitting?: boolean;
  onSubmit: () => void;
}

/** Order-set summary plus submit button, above the tab bar. */
export function SubmitBar({ draftsCount, cancelCount, locked, submitting = false, onSubmit }: SubmitBarProps) {
  const nothingToCommit = draftsCount === 0 && cancelCount === 0;
  return (
    <div className={styles.row}>
      <div className={styles.info}>
        {locked ? (
          <>
            <div className={styles.summary}>Order set submitted</div>
            <div className={styles.note}>A new set unlocks tomorrow</div>
          </>
        ) : (
          <>
            <div className={styles.summary}>
              {draftsCount} new &middot; {cancelCount} cancel
            </div>
            <div className={styles.note}>Locks at end of day</div>
          </>
        )}
      </div>
      <button
        type="button"
        className={styles.submitBtn}
        onClick={onSubmit}
        disabled={locked || submitting || nothingToCommit}
      >
        {submitting ? "Submitting\u2026" : "Submit \u21B5"}
      </button>
    </div>
  );
}
