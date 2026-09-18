import { useState } from "react";

import { useCandles } from "../hooks/useCandles";
import { marketService } from "../services/MarketService";
import type { SymbolQuote } from "../types";
import { formatSignedPercent, formatSignedUsd, formatUsd } from "../utils/format";
import { CandleChart } from "./CandleChart";
import { StatusNote } from "./StatusNote";
import styles from "./QuoteDetail.module.css";

interface QuoteDetailProps {
  quote: SymbolQuote;
}

/**
 * Selected-symbol header, candlestick chart, and timeframe chips. The change
 * next to the price is the displayed period's change: the first candle's
 * open vs. the last candle's close, so it follows the selected timeframe.
 */
export function QuoteDetail({ quote }: QuoteDetailProps) {
  const timeframes = marketService.listTimeframes();
  const [selectedTimeframe, setSelectedTimeframe] = useState(timeframes[1].label);

  const timeframe =
    timeframes.find((candidate) => candidate.label === selectedTimeframe) ?? timeframes[1];
  const candles = useCandles(quote, timeframe);

  const series = candles.data;
  const periodStart = series?.[0];
  const periodEnd = series?.[series.length - 1];
  const changeAbs =
    periodStart != null && periodEnd != null ? periodEnd.close - periodStart.open : quote.changeAbs;
  const changePct =
    periodStart != null && periodEnd != null && periodStart.open !== 0
      ? ((periodEnd.close - periodStart.open) / periodStart.open) * 100
      : quote.changePct;
  const quoteUp = changeAbs >= 0;

  return (
    <section>
      <div className={styles.quoteRow}>
        <div>
          <div className={styles.quoteSymbol}>{quote.symbol}</div>
          <div className={styles.quotePrice}>{formatUsd(quote.price)}</div>
        </div>
        <div className={styles.quoteChange}>
          <div className={`${styles.changeAbs} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedUsd(changeAbs, 2)}
          </div>
          <div className={`${styles.changePct} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedPercent(changePct, 2)}
          </div>
        </div>
      </div>

      <div className={styles.chart}>
        {series != null ? (
          <CandleChart data={series} />
        ) : (
          <StatusNote
            tone={candles.error == null ? "loading" : "error"}
            message={candles.error ?? undefined}
            onRetry={candles.error == null ? undefined : candles.reload}
          />
        )}
      </div>

      <div className={styles.timeframes}>
        {timeframes.map((timeframeOption) => (
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
