import { useEffect } from "react";

import { marketService } from "../services/MarketService";

/**
 * Fire-and-forget prefetch of every chart timeframe's price window, so
 * switching timeframes later resolves from memory or an in-flight request
 * instead of waiting on a fresh fetch (the year-long window is the slow one).
 */
export function useTimeframePrefetch() {
  useEffect(() => {
    marketService.prefetchTimeframes();
  }, []);
}
