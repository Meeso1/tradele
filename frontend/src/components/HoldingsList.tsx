import { CASH, HOLDINGS } from "../mock/data";
import { formatSignedPercent, formatSignedUsd, formatWholeUsd } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import styles from "./HoldingsList.module.css";

/** Holdings table plus the cash row (Portfolio screen). */
export function HoldingsList() {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>Holdings</SectionTitle>
      </div>
      {HOLDINGS.map((holding) => {
        const up = holding.pnlAbs >= 0;
        return (
          <div key={holding.symbol} className={styles.row}>
            <div className={styles.main}>
              <div className={styles.top}>
                <span className={styles.symbol}>{holding.symbol}</span>
                <span className={holding.side === "long" ? styles.chipLong : styles.chipShort}>
                  {holding.side.toUpperCase()}
                </span>
              </div>
              <div className={styles.basis}>
                {holding.shares} @ {holding.avgPrice.toFixed(2)}
              </div>
            </div>
            <div className={styles.col}>
              <div className={styles.last}>{holding.lastPrice.toFixed(2)}</div>
              <div className={styles.lastLabel}>last</div>
            </div>
            <div className={styles.col}>
              <div className={up ? styles.pnlUp : styles.pnlDown}>
                {formatSignedUsd(holding.pnlAbs)}
              </div>
              <div className={up ? styles.pnlUpSmall : styles.pnlDownSmall}>
                {formatSignedPercent(holding.pnlPct)}
              </div>
            </div>
          </div>
        );
      })}
      <div className={styles.cashRow}>
        <span className={styles.cashLabel}>CASH</span>
        <span className={styles.cashValue}>{formatWholeUsd(CASH)}</span>
      </div>
    </section>
  );
}
