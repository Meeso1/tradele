/**
 * Raw request/response shapes mirrored from the backend DTOs
 * (`app/dtos/*.py`). Everything the API layer passes around before mapping
 * into the domain types in `types.ts` uses these.
 */

/** Backend `HourlyDate` (pydantic dataclass): a day plus the hour within it. */
export interface HourlyDateDto {
  day: string; // "2026-09-17"
  hour: number;
}

/** Backend `PriceHistoryRange` enum (convenience ranges for `/market/prices`). */
export type PriceHistoryRangeDto = "current_hour" | "day" | "week" | "month" | "year";

export interface HourlyPriceDataDto {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  starting_hour: HourlyDateDto;
}

export interface MarketStateResponseDto {
  hour: HourlyDateDto;
  prices: Record<string, HourlyPriceDataDto>;
  market_open: boolean;
}

export interface PortfolioResponseDto {
  cash: number;
  holdings: Record<string, number>;
}

export interface PortfolioStateResponseDto {
  cash: number;
  holdings: Record<string, number>;
  timestamp: HourlyDateDto;
  total_value: number;
  recorded_at: string;
}

export type TradeKindDto =
  | "market_buy"
  | "market_sell"
  | "limit_buy"
  | "limit_sell"
  | "stop_buy"
  | "stop_sell";

export type InactiveTradeStatusDto =
  | "executed"
  | "cancelled"
  | "error"
  | "insufficient_funds"
  | "symbol_unavailable"
  | "malformed_request";

export interface ActiveTradeDto {
  id: string;
  user_id: string;
  symbol: string;
  kind: TradeKindDto;
  requested_price: number | null;
  quantity: number | null;
  value: number | null;
  requested_at: string;
  active_from: HourlyDateDto;
}

export interface HistoricalTradeDto {
  id: string;
  user_id: string;
  symbol: string;
  kind: TradeKindDto;
  requested_price: number | null;
  quantity: number | null;
  value: number | null;
  requested_at: string;
  active_from: HourlyDateDto;
  fill_price: number | null;
  closed_at: string;
  closed_at_hour: HourlyDateDto;
  status: InactiveTradeStatusDto;
}

export interface TradesResponseDto {
  requested: ActiveTradeDto[];
  closed: HistoricalTradeDto[];
}

export interface HasSubmittedTodayResponseDto {
  has_submitted_today: boolean;
}

export interface TradeInputDto {
  symbol: string;
  kind: TradeKindDto;
  /** Either quantity or value must be set, but not both. */
  quantity?: number;
  value?: number;
  /** Required for limit/stop orders; ignored for market orders. */
  requested_price?: number;
}

export interface SubmitTradesRequestDto {
  new_trades: TradeInputDto[];
  trades_to_cancel: string[];
}

export interface SubmitTradesResponseDto {
  submitted_ids: string[];
  cancelled_ids: string[];
}

export interface MetadataResponseDto {
  day_number: number;
  seconds_until_day_end: number;
}

export interface CreateUserResponseDto {
  id: string;
}

export interface IssueTokenResponseDto {
  access_token: string;
  token_type: string;
}
