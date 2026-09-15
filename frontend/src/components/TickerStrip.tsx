import { QUOTES } from "../mock/data";
import { formatSignedPercent } from "../utils/format";
import styles from "./TickerStrip.module.css";

interface TickerStripProps {
  selectedSymbol: string;
  onSelect: (symbol: string) => void;
}

/** Horizontally scrolling watchlist chips; the selected one is highlighted. */
export function TickerStrip({ selectedSymbol, onSelect }: TickerStripProps) {
  return (
    <div className={styles.strip}>
      {QUOTES.map((ticker) => {
        const selected = ticker.symbol === selectedSymbol;
        const tickerUp = ticker.changePct >= 0;
        return (
          <button
            key={ticker.symbol}
            type="button"
            className={selected ? styles.tickerActive : styles.ticker}
            onClick={() => onSelect(ticker.symbol)}
          >
            <div className={styles.tickerSymbol}>{ticker.symbol}</div>
            <div
              className={
                selected
                  ? styles.tickerChangeSelected
                  : tickerUp
                    ? styles.tickerChangeUp
                    : styles.tickerChangeDown
              }
            >
              {formatSignedPercent(ticker.changePct)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
