/**
 * Shared domain types.
 *
 * Data types are immutable (all-`readonly`, like Python dataclasses). Mutable
 * UI state is never mixed into them - it lives in separate `*State` types that
 * wrap a data object (e.g. `OpenOrderState`).
 */

/** Top-level app tab. */
export type Tab = "market" | "portfolio";

export type OrderType = "market" | "limit" | "stop";
export type OrderSide = "buy" | "sell";
export type QtyMode = "shares" | "value";

/** Terminal statuses of a past (settled) order. */
export type OrderStatus =
  | "filled"
  | "cancelled"
  | "error"
  | "no_funds"
  | "delisted";

/**
 * Order quantity exactly as the user specified it. The client never converts
 * between shares and dollar value - the backend (or execution time) does, to
 * avoid discrepancies with e.g. market orders.
 */
export type OrderQuantity =
  | { readonly shares: number }
  | { readonly value: number };

export interface Candle {
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
}

/** Chart timeframe option for the quote-detail candlesticks. */
export interface Timeframe {
  readonly label: string;
  /** Candle interval shown under the label. */
  readonly interval: string;
  readonly points: number;
}

/** Change over a period: absolute and percent. */
export interface PriceChange {
  readonly abs: number;
  readonly pct: number;
}

export interface SymbolQuote {
  readonly symbol: string;
  readonly price: number;
  readonly changeAbs: number;
  readonly changePct: number;
}

/** An order that is currently live on the market. */
export interface OpenOrder {
  readonly id: string;
  readonly side: OrderSide;
  readonly type: OrderType;
  readonly symbol: string;
  readonly quantity: OrderQuantity;
  /** Limit/stop price; undefined for market orders. */
  readonly price?: number;
}

/** An `OpenOrder` plus mutable view state. */
export interface OpenOrderState {
  readonly order: OpenOrder;
  /** True once the user hit Cancel but before the set is submitted. */
  cancelling: boolean;
}

/** A drafted order in today's "New today" set (not submitted yet). */
export interface NewOrder {
  readonly id: string;
  readonly side: OrderSide;
  readonly type: OrderType;
  readonly symbol: string;
  readonly quantity: OrderQuantity;
  readonly price?: number;
}

export interface OrderDetailField {
  readonly label: string;
  readonly value: string;
}

/** Content of the order-details bottom sheet. */
export interface OrderDetails {
  readonly status: OrderStatus;
  readonly title: string;
  readonly reason: string | null;
  readonly fields: readonly OrderDetailField[];
}

export interface HistoryOrder {
  readonly id: string;
  readonly status: OrderStatus;
  /** One-line summary, e.g. "BUY 60 HLIX @ 128.40". */
  readonly label: string;
  readonly details: OrderDetails;
}

/** All trades that were closed (executed, cancelled, ...) during one day. */
export interface HistoryDay {
  readonly date: string;
  readonly orders: readonly HistoryOrder[];
}

export interface Holding {
  readonly symbol: string;
  readonly shares: number;
  readonly lastPrice: number;
}
