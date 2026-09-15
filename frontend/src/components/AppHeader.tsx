import { DAY_NUMBER } from "../mock/data";
import { hoursUntilEndOfDay } from "../utils/time";
import styles from "./AppHeader.module.css";

export function AppHeader() {
  // Relative countdown instead of an absolute end-of-day time, which would
  // depend on the viewer's timezone.
  const hoursLeft = hoursUntilEndOfDay();
  return (
    <header className={styles.header}>
      <div className={styles.row}>
        <div className={styles.wordmark}>Tradele</div>
        <div className={styles.meta}>
          <span className={styles.dayChip}>DAY {DAY_NUMBER}</span>
          <span className={styles.hoursLeft}>{hoursLeft}h left</span>
        </div>
      </div>
    </header>
  );
}
