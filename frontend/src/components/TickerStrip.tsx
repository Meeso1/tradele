import { useEffect, useRef } from "react";

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
  const stripRef = useRef<HTMLDivElement>(null);

  // The scrollbar is hidden by design, so vertical wheel input is translated
  // into horizontal scrolling. React registers `wheel` as a passive listener
  // (preventDefault would be ignored there), hence the native listener.
  useEffect(() => {
    const strip = stripRef.current;
    if (strip == null) return;

    const handleWheel = (event: WheelEvent) => {
      const maxScrollLeft = strip.scrollWidth - strip.clientWidth;
      if (maxScrollLeft <= 0) return;

      // Shift+wheel arrives as deltaX in some browsers, plain wheel as
      // deltaY; Firefox reports lines instead of pixels.
      const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
      const pixelsPerLine = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 40 : 1;
      const scrollBy = delta * pixelsPerLine;

      // At either edge, let the wheel scroll the page instead.
      const pastEdge =
        (scrollBy < 0 && strip.scrollLeft <= 0) ||
        (scrollBy > 0 && strip.scrollLeft >= maxScrollLeft);
      if (pastEdge) return;

      event.preventDefault();
      strip.scrollLeft += scrollBy;
    };

    strip.addEventListener("wheel", handleWheel, { passive: false });
    return () => strip.removeEventListener("wheel", handleWheel);
  }, []);

  return (
    <div ref={stripRef} className={styles.strip}>
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
