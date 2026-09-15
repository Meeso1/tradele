import { CASH, HOLDINGS } from "../mock/data";
import { formatShares, formatWholeUsd } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import styles from "./HoldingsList.module.css";

/** Holdings table plus the cash row (Portfolio screen). */
export function HoldingsList() {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>Holdings</SectionTitle>
      </div>
      {HOLDINGS.map((holding) => (
        <div key={holding.symbol} className={styles.row}>
          <div className={styles.main}>
            <div className={styles.symbol}>{holding.symbol}</div>
            <div className={styles.shares}>{formatShares(holding.shares)} sh</div>
          </div>
          <div className={styles.col}>
            <div className={styles.last}>{holding.lastPrice.toFixed(2)}</div>
            <div className={styles.lastLabel}>last</div>
          </div>
        </div>
      ))}
      <div className={styles.cashRow}>
        <span className={styles.cashLabel}>CASH</span>
        <span className={styles.cashValue}>{formatWholeUsd(CASH)}</span>
      </div>
    </section>
  );
}
