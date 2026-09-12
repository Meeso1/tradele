import { useMemo, useState } from "react";

import { PORTFOLIO_RANGES, PORTFOLIO_VALUE, SINCE_SUBMIT, seriesFor } from "../mock/data";
import { formatSignedPercent, formatSignedUsd, formatWholeUsd } from "../utils/format";
import { AreaChart } from "./AreaChart";
import { SectionTitle } from "./SectionTitle";
import styles from "./PortfolioSummary.module.css";

/** Hero block of the Portfolio screen: value, period chart, and range picker. */
export function PortfolioSummary() {
  const [selectedRange, setSelectedRange] = useState(PORTFOLIO_RANGES[1].label);

  const range =
    PORTFOLIO_RANGES.find((candidate) => candidate.label === selectedRange) ?? PORTFOLIO_RANGES[1];
  const series = useMemo(() => seriesFor(range), [range]);
  const changeUp = range.changeAbs >= 0;

  return (
    <section>
      <div className={styles.valueBlock}>
        <SectionTitle>Portfolio value</SectionTitle>
        <div className={styles.value}>{formatWholeUsd(PORTFOLIO_VALUE)}</div>
        <div className={styles.sinceChip}>
          <span className={styles.sinceAbs}>&#9650; {formatSignedUsd(SINCE_SUBMIT.abs)}</span>
          <span className={styles.sinceNote}>
            {formatSignedPercent(SINCE_SUBMIT.pct, 2)} since last submit
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
          &#9650; {formatSignedUsd(range.changeAbs)}
        </span>
        <span className={styles.changePct}>{formatSignedPercent(range.changePct)}</span>
        <span className={styles.changeNote}>&middot; {range.note}</span>
      </div>
      <div className={styles.ranges}>
        {PORTFOLIO_RANGES.map((portfolioRange) => (
          <button
            key={portfolioRange.label}
            type="button"
            className={portfolioRange.label === selectedRange ? styles.rangeActive : styles.range}
            onClick={() => setSelectedRange(portfolioRange.label)}
          >
            {portfolioRange.label}
          </button>
        ))}
      </div>
    </section>
  );
}
