import { useAsync } from "./useAsync";
import type { PortfolioOverview } from "../api/mappers";
import { portfolioService } from "../services/PortfolioService";

/** Cash, holdings (with last prices) and total portfolio value. */
export function usePortfolioOverview() {
  return useAsync<PortfolioOverview>(() => portfolioService.getOverview(), []);
}
