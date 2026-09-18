import { apiGet } from "../api/client";
import type { MetadataResponseDto } from "../api/dto";

export interface DayInfo {
  /** Day number of the game, e.g. 128. */
  dayNumber: number;
  /** Whole hours left in the current game day (at least 1). */
  hoursLeft: number;
}

/** Game-day metadata, backed by the real `/metadata` endpoint. */
export class MetadataService {
  async getDayInfo(): Promise<DayInfo> {
    const dto = await apiGet<MetadataResponseDto>("/metadata");
    return {
      dayNumber: dto.day_number,
      hoursLeft: Math.max(1, Math.ceil(dto.seconds_until_day_end / 3_600)),
    };
  }
}

export const metadataService = new MetadataService();
