import { useState } from "react";

import { usePortfolioSummary } from "../hooks/usePortfolioSummary";
import type { PortfolioOverview } from "../api/mappers";
import { portfolioService } from "../services/PortfolioService";
import { formatSignedPercent, formatSignedUsd, formatWholeUsd } from "../utils/format";
import { AreaChart } from "./AreaChart";
import { SectionTitle } from "./SectionTitle";
import { StatusNote } from "./StatusNote";
import styles from "./PortfolioSummary.module.css";

interface PortfolioSummaryProps {
  /** Null while the portfolio overview is still loading. */
  overview: PortfolioOverview | null;
}

/** Hero block of the Portfolio screen: value, period chart, and range picker. */
export function PortfolioSummary({ overview }: PortfolioSummaryProps) {
  const ranges = portfolioService.listRanges();
  const [selectedRange, setSelectedRange] = useState(ranges[1].label);
  const summary = usePortfolioSummary(selectedRange, overview);

  if (summary.data == null) {
    return (
      <StatusNote
        tone={summary.error == null ? "loading" : "error"}
        message={summary.error ?? undefined}
        onRetry={summary.error == null ? undefined : summary.reload}
      />
    );
  }

  const { value, sinceSubmit, series, changeAbs, changePct, note } = summary.data;
  const changeUp = changeAbs >= 0;

  return (
    <section>
      <div className={styles.valueBlock}>
        <SectionTitle>Portfolio value</SectionTitle>
        <div className={styles.value}>{formatWholeUsd(value)}</div>
        <div className={styles.sinceChip}>
          <span className={styles.sinceAbs}>&#9650; {formatSignedUsd(sinceSubmit.abs)}</span>
          <span className={styles.sinceNote}>
            {formatSignedPercent(sinceSubmit.pct, 2)} since last submit
          </span>
        </div>
      </div>

      <div className={styles.chart}>
        <AreaChart
          series={series}
          stroke="var(--up)"
          gradientId="portfolio-area"
          fillTop="rgba(63,125,83,.22)"
          fillBottom="rgba(63,125,83,0)"
        />
      </div>
      <div className={styles.changeRow}>
        <span className={changeUp ? styles.changeUp : styles.changeDown}>
          &#9650; {formatSignedUsd(changeAbs)}
        </span>
        <span className={styles.changePct}>{formatSignedPercent(changePct)}</span>
        <span className={styles.changeNote}>&middot; {note}</span>
      </div>
      <div className={styles.ranges}>
        {ranges.map((range) => (
          <button
            key={range.label}
            type="button"
            className={range.label === selectedRange ? styles.rangeActive : styles.range}
            onClick={() => setSelectedRange(range.label)}
          >
            {range.label}
          </button>
        ))}
      </div>
    </section>
  );
}
