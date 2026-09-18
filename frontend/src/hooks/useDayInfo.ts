import { useAsync } from "./useAsync";
import { metadataService, type DayInfo } from "../services/MetadataService";

/** Game-day metadata (day number, hours left in the day). */
export function useDayInfo() {
  return useAsync<DayInfo>(() => metadataService.getDayInfo(), []);
}
