import { useAsync } from "./useAsync";
import { tradesService, type TradesData } from "../services/TradesService";

/** Open (requested) trades and closed-trade history for the signed-in player. */
export function useTrades() {
  return useAsync<TradesData>(() => tradesService.getTrades(), []);
}
