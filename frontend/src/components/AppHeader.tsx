import { ISSUE_NUMBER, MARKET_STATUS } from "../mock/data";
import { hoursUntilEndOfDay } from "../utils/time";
import styles from "./AppHeader.module.css";

interface AppHeaderProps {
  /** Show the "MARKET OPEN" status line (Market screen only). */
  showMarketStatus?: boolean;
}

export function AppHeader({ showMarketStatus = false }: AppHeaderProps) {
  // Relative countdown instead of an absolute lock time, which would depend on
  // the viewer's timezone.
  const hoursLeft = hoursUntilEndOfDay();
  return (
    <header className={styles.header}>
      <div className={styles.row}>
        <div className={styles.wordmark}>Tradele</div>
        <div className={styles.meta}>
          <span className={styles.issue}>{ISSUE_NUMBER}</span>
          <span className={styles.hoursLeft}>{hoursLeft}h left</span>
        </div>
      </div>
      {showMarketStatus && MARKET_STATUS.open && (
        <div className={styles.status}>
          <span className={styles.statusDot} />
          MARKET OPEN
        </div>
      )}
    </header>
  );
}
