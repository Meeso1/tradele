import { apiGet } from "../api/client";
import type { MarketStateResponseDto, PortfolioResponseDto } from "../api/dto";
import { mapPortfolioOverview, type PortfolioOverview } from "../api/mappers";
import { PORTFOLIO_RANGES, SINCE_SUBMIT, seriesFor, type PortfolioRange } from "../mock/data";

export interface SinceSubmitChange {
  readonly abs: number;
  readonly pct: number;
}

export interface ValueSeries {
  readonly series: number[];
  readonly note: string;
}

export interface PortfolioRangeInfo {
  readonly label: string;
  readonly note: string;
}

export interface PortfolioSummary {
  readonly value: number;
  readonly sinceSubmit: SinceSubmitChange;
  readonly series: number[];
  readonly changeAbs: number;
  readonly changePct: number;
  readonly note: string;
}

/**
 * Portfolio backed by the `/portfolio` + `/market/prices` endpoints.
 */
export class PortfolioService {
  /** Cash, holdings (with last prices) and total value for the signed-in player. */
  async getOverview(): Promise<PortfolioOverview> {
    const [portfolio, priceStates] = await Promise.all([
      apiGet<PortfolioResponseDto>("/portfolio"),
      apiGet<MarketStateResponseDto[]>("/market/prices"),
    ]);
    return mapPortfolioOverview(portfolio, priceStates[priceStates.length - 1]);
  }

  /** Range options for the portfolio-value chart. */
  listRanges(): readonly PortfolioRangeInfo[] {
    return PORTFOLIO_RANGES.map(({ label, note }) => ({ label, note }));
  }

  /**
   * Portfolio-value series for a range.
   *
   * TODO: no portfolio-history endpoint exists yet - return the real value
   * series once it does; the current series comes from the seeded
   * generators in `mock/data.ts`, scaled to the current value so the chart
   * ends where the hero value is.
   */
  async getValueSeries(rangeLabel: string, currentValue: number): Promise<ValueSeries> {
    const range = findRange(rangeLabel);
    return { series: seriesFor(range, currentValue), note: range.note };
  }

  /**
   * Portfolio change since the last daily submission.
   *
   * TODO: no portfolio-snapshot endpoint exists yet - compute from real
   * snapshots once they do; the current value comes from `mock/data.ts`.
   */
  async getSinceSubmitChange(): Promise<SinceSubmitChange> {
    return SINCE_SUBMIT;
  }

  /** Hero summary: current value, series and change for the selected range. */
  async getSummary(rangeLabel: string, currentValue: number): Promise<PortfolioSummary> {
    const [seriesInfo, sinceSubmit] = await Promise.all([
      this.getValueSeries(rangeLabel, currentValue),
      this.getSinceSubmitChange(),
    ]);
    const first = seriesInfo.series[0];
    const last = seriesInfo.series[seriesInfo.series.length - 1];
    const changeAbs = last - first;
    const changePct = first !== 0 ? (changeAbs / Math.abs(first)) * 100 : 0;
    return {
      value: currentValue,
      sinceSubmit,
      series: seriesInfo.series,
      changeAbs,
      changePct,
      note: seriesInfo.note,
    };
  }
}

function findRange(rangeLabel: string): PortfolioRange {
  return (
    PORTFOLIO_RANGES.find((candidate) => candidate.label === rangeLabel) ?? PORTFOLIO_RANGES[0]
  );
}

export const portfolioService = new PortfolioService();
