import { apiGet, apiPost } from "../api/client";
import type {
  HasSubmittedTodayResponseDto,
  SubmitTradesRequestDto,
  SubmitTradesResponseDto,
  TradesResponseDto,
} from "../api/dto";
import {
  mapActiveTradeToOpenOrder,
  mapClosedTradesToHistory,
  mapDraftToTradeInput,
} from "../api/mappers";
import type { HistoryDay, NewOrder, OpenOrder } from "../types";

export interface TradesData {
  /** Trades still working on the market (the day's open orders). */
  openOrders: OpenOrder[];
  /** Closed trades grouped by the day they were closed, most recent first. */
  history: HistoryDay[];
}

/** Trade submission and history, backed by the real `/trades` endpoints. */
export class TradesService {
  /** Requested (still-working) and closed trades for the signed-in player. */
  async getTrades(): Promise<TradesData> {
    const dto = await apiGet<TradesResponseDto>("/trades");
    return {
      openOrders: dto.requested.map(mapActiveTradeToOpenOrder),
      history: mapClosedTradesToHistory(dto.closed),
    };
  }

  /** Whether today's single order-set submission was already used. */
  async hasSubmittedToday(): Promise<boolean> {
    const dto = await apiGet<HasSubmittedTodayResponseDto>("/trades/has-submitted-today");
    return dto.has_submitted_today;
  }

  /**
   * Submit the day's single order set: the drafted new trades plus the open
   * orders marked for cancellation.
   */
  async submit(
    drafts: readonly NewOrder[],
    cancelIds: readonly string[],
  ): Promise<SubmitTradesResponseDto> {
    const body: SubmitTradesRequestDto = {
      new_trades: drafts.map(mapDraftToTradeInput),
      trades_to_cancel: [...cancelIds],
    };
    return apiPost<SubmitTradesResponseDto>("/trades", body);
  }
}

export const tradesService = new TradesService();
