import { useAsync } from "./useAsync";
import { marketService } from "../services/MarketService";

/** Current hourly quotes for every tradable symbol. */
export function useQuotes() {
  return useAsync(() => marketService.getQuotes(), []);
}
