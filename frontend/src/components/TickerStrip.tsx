import type { PriceChange, SymbolQuote } from "../types";
import { formatSignedPercent } from "../utils/format";
import styles from "./TickerStrip.module.css";

interface TickerStripProps {
  quotes: readonly SymbolQuote[];
  /** Daily change per symbol (see `useDailyChanges`). */
  changes: Readonly<Record<string, PriceChange>>;
  selectedSymbol: string;
  onSelect: (symbol: string) => void;
}

/** Horizontally scrolling watchlist chips; the selected one is highlighted. */
export function TickerStrip({ quotes, changes, selectedSymbol, onSelect }: TickerStripProps) {
  return (
    <div className={styles.strip}>
      {quotes.map((ticker) => {
        const selected = ticker.symbol === selectedSymbol;
        const change = changes[ticker.symbol];
        const tickerUp = change != null ? change.pct >= 0 : true;
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
              {change != null ? formatSignedPercent(change.pct) : "\u2014"}
            </div>
          </button>
        );
      })}
    </div>
  );
}
