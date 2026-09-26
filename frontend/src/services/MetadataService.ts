import { apiGet, apiPost } from "../api/client";
import type { MetadataResponseDto } from "../api/dto";

export interface DayInfo {
  /** Day number of the game, e.g. 128. */
  dayNumber: number;
  /** Whole hours left in the current game day (at least 1). */
  hoursLeft: number;
  /** Whether the current user has completed the tutorial. */
  hasCompletedTutorial: boolean;
}

/** Game-day metadata, backed by the real `/metadata` endpoint. */
export class MetadataService {
  async getDayInfo(): Promise<DayInfo> {
    const dto = await apiGet<MetadataResponseDto>("/metadata");
    return {
      dayNumber: dto.day_number,
      hoursLeft: Math.max(1, Math.ceil(dto.seconds_until_day_end / 3_600)),
      hasCompletedTutorial: dto.has_completed_tutorial,
    };
  }

  /** Mark the current user's tutorial as completed (idempotent). */
  async completeTutorial(): Promise<void> {
    await apiPost<null>("/metadata/complete-tutorial");
  }
}

export const metadataService = new MetadataService();
