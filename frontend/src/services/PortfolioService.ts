import { apiGet } from "../api/client";
import type { PortfolioResponseDto, PortfolioStateResponseDto } from "../api/dto";
import {
  mapPortfolioHistoryToSeries,
  mapPortfolioOverview,
  type PortfolioOverview,
} from "../api/mappers";
import { marketService } from "./MarketService";
import { SINCE_SUBMIT } from "../mock/data";

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

/** How one UI range maps onto the `/portfolio/history` endpoint. */
interface PortfolioRangeSpec {
  readonly label: string;
  readonly note: string;
  /** Trailing window in days, resolved against the client clock. */
  readonly startDays: number | null;
}

const PORTFOLIO_RANGES: readonly PortfolioRangeSpec[] = [
  { label: "1W", note: "past week", startDays: 7 },
  { label: "1M", note: "past month", startDays: 30 },
  { label: "3M", note: "past 3 months", startDays: 90 },
  { label: "1Y", note: "past year", startDays: 365 },
  { label: "ALL", note: "all time", startDays: null },
];

/**
 * Portfolio backed by the `/portfolio` + `/portfolio/history` endpoints;
 * last prices for valuing holdings come from MarketService's shared market
 * snapshot (no separate fetch).
 */
export class PortfolioService {
  /** Cash, holdings (with last prices) and total value for the signed-in player. */
  async getOverview(): Promise<PortfolioOverview> {
    const [portfolio, lastPrices] = await Promise.all([
      apiGet<PortfolioResponseDto>("/portfolio"),
      marketService.getLatestPrices(),
    ]);
    return mapPortfolioOverview(portfolio, lastPrices);
  }

  /** Range options for the portfolio-value chart. */
  listRanges(): readonly PortfolioRangeInfo[] {
    return PORTFOLIO_RANGES.map(({ label, note }) => ({ label, note }));
  }

  /** Portfolio-value series for a range, from the recorded hourly states. */
  async getValueSeries(rangeLabel: string, currentValue: number): Promise<ValueSeries> {
    const range = findRange(rangeLabel);
    const states = await apiGet<PortfolioStateResponseDto[]>(
      `/portfolio/history${historyQuery(range.startDays)}`,
    );
    return { series: mapPortfolioHistoryToSeries(states, currentValue), note: range.note };
  }

  /**
   * Portfolio change since the last daily submission.
   *
   * TODO: no endpoint exposes the portfolio value at the last submission
   * (the submission timestamp lives server-side only) - compute from a real
   * snapshot once one does; the current value comes from `mock/data.ts`.
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

function findRange(rangeLabel: string): PortfolioRangeSpec {
  return (
    PORTFOLIO_RANGES.find((candidate) => candidate.label === rangeLabel) ?? PORTFOLIO_RANGES[0]
  );
}

function historyQuery(startDays: number | null): string {
  if (startDays == null) return "";
  const start = new Date(Date.now() - startDays * 86_400_000);
  return `?start=${start.toISOString()}`;
}

export const portfolioService = new PortfolioService();
