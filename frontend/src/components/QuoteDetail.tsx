import { useMemo, useState } from "react";

import { TIMEFRAMES, candlesFor } from "../mock/data";
import type { SymbolQuote } from "../types";
import { formatSignedPercent, formatSignedUsd, formatUsd } from "../utils/format";
import { CandleChart } from "./CandleChart";
import styles from "./QuoteDetail.module.css";

interface QuoteDetailProps {
  quote: SymbolQuote;
}

/** Selected-symbol header, candlestick chart, and timeframe chips. */
export function QuoteDetail({ quote }: QuoteDetailProps) {
  const [selectedTimeframe, setSelectedTimeframe] = useState(TIMEFRAMES[1].label);

  const timeframe =
    TIMEFRAMES.find((candidate) => candidate.label === selectedTimeframe) ?? TIMEFRAMES[1];
  const candles = useMemo(() => candlesFor(quote, timeframe), [quote, timeframe]);
  const quoteUp = quote.changeAbs >= 0;

  return (
    <section>
      <div className={styles.quoteRow}>
        <div>
          <div className={styles.quoteSymbol}>{quote.symbol}</div>
          <div className={styles.quotePrice}>{formatUsd(quote.price)}</div>
        </div>
        <div className={styles.quoteChange}>
          <div className={`${styles.changeAbs} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedUsd(quote.changeAbs, 2)}
          </div>
          <div className={`${styles.changePct} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedPercent(quote.changePct, 2)}
          </div>
        </div>
      </div>

      <div className={styles.chart}>
        <CandleChart data={candles} />
      </div>

      <div className={styles.timeframes}>
        {TIMEFRAMES.map((timeframeOption) => (
          <button
            key={timeframeOption.label}
            type="button"
            className={timeframeOption.label === selectedTimeframe ? styles.tfActive : styles.tf}
            onClick={() => setSelectedTimeframe(timeframeOption.label)}
          >
            <div className={styles.tfLabel}>{timeframeOption.label}</div>
            <div className={styles.tfInterval}>{timeframeOption.interval}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
