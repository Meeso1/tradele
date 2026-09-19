import { useAsync } from "./useAsync";
import { marketService } from "../services/MarketService";

/**
 * Daily (first open → last close) change per symbol over the most recent
 * trading day, derived from MarketService's shared market snapshot.
 */
export function useDailyChanges() {
  return useAsync(() => marketService.getDailyChanges(), []);
}
