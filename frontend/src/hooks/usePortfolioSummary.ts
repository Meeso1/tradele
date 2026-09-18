import { useAsync } from "./useAsync";
import type { PortfolioOverview } from "../api/mappers";
import { portfolioService, type PortfolioSummary } from "../services/PortfolioService";

/**
 * Hero summary data for the selected range. Returns null data while
 * `overview` is still loading (the series is scaled to the current value).
 */
export function usePortfolioSummary(rangeLabel: string, overview: PortfolioOverview | null) {
  return useAsync<PortfolioSummary | null>(async () => {
    if (overview == null) return null;
    return portfolioService.getSummary(rangeLabel, overview.value);
  }, [rangeLabel, overview]);
}
