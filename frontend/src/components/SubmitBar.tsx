import styles from "./SubmitBar.module.css";

interface SubmitBarProps {
  draftsCount: number;
  cancelCount: number;
  onSubmit: () => void;
}

/** Order-set summary plus submit button, above the tab bar. */
export function SubmitBar({ draftsCount, cancelCount, onSubmit }: SubmitBarProps) {
  return (
    <div className={styles.row}>
      <div className={styles.info}>
        <div className={styles.summary}>
          {draftsCount} new &middot; {cancelCount} cancel
        </div>
        <div className={styles.note}>Locks at market close</div>
      </div>
      <button type="button" className={styles.submitBtn} onClick={onSubmit}>
        Submit &crarr;
      </button>
    </div>
  );
}
