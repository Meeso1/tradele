import { useDayInfo } from "../hooks/useDayInfo";
import styles from "./AppHeader.module.css";

export function AppHeader() {
  const dayInfo = useDayInfo();
  return (
    <header className={styles.header}>
      <div className={styles.row}>
        <div className={styles.wordmark}>Tradele</div>
        <div className={styles.meta}>
          {dayInfo.data != null && (
            <>
              <span className={styles.dayChip}>DAY {dayInfo.data.dayNumber}</span>
              <span className={styles.hoursLeft}>{dayInfo.data.hoursLeft}h left</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
