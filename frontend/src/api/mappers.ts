/**
 * Mappers from the raw API DTOs (`api/dto.ts`) to the domain types in
 * `types.ts`. All API-response → UI-shape translation lives here so
 * components and services never touch raw DTOs.
 */

import type {
  Candle,
  HistoryDay,
  HistoryOrder,
  Holding,
  NewOrder,
  OpenOrder,
  OrderDetailField,
  OrderDetails,
  OrderQuantity,
  OrderSide,
  OrderStatus,
  OrderType,
  PriceChange,
  SymbolQuote,
} from "../types";
import { formatDayLabel, formatShares, formatWholeUsd } from "../utils/format";
import type {
  ActiveTradeDto,
  HistoricalTradeDto,
  HourlyDateDto,
  HourlyPriceDataDto,
  InactiveTradeStatusDto,
  MarketStateResponseDto,
  PortfolioResponseDto,
  PortfolioStateResponseDto,
  TradeInputDto,
  TradeKindDto,
} from "./dto";

/* -------------------------------------------------------------------------- */
/* Market                                                                      */
/* -------------------------------------------------------------------------- */

/** Quotes sorted by symbol; change is the hourly open→close move. */
export function mapPricesToQuotes(dto: MarketStateResponseDto): SymbolQuote[] {
  return Object.values(dto.prices)
    .map(mapHourlyPriceToQuote)
    .sort((first, second) => first.symbol.localeCompare(second.symbol));
}

function mapHourlyPriceToQuote(dto: HourlyPriceDataDto): SymbolQuote {
  const changeAbs = dto.close - dto.open;
  const changePct = dto.open !== 0 ? (changeAbs / dto.open) * 100 : 0;
  return { symbol: dto.symbol, price: dto.close, changeAbs, changePct };
}

/**
 * Aggregate a contiguous run of hourly market states into candles for one
 * symbol: every `bucketHours` states form one candle (open of the first
 * priced hour, close of the last, extremes across the bucket). Hours with no
 * price for the symbol (market closed) are skipped, as are buckets with no
 * priced hours at all.
 */
export function mapStatesToCandles(
  states: readonly MarketStateResponseDto[],
  symbol: string,
  bucketHours: number,
): Candle[] {
  const candles: Candle[] = [];
  for (let start = 0; start < states.length; start += bucketHours) {
    const priced = states
      .slice(start, start + bucketHours)
      .map((state) => state.prices[symbol])
      .filter((price) => price != null);
    if (priced.length === 0) continue;
    candles.push({
      open: priced[0].open,
      close: priced[priced.length - 1].close,
      high: Math.max(...priced.map((price) => price.high)),
      low: Math.min(...priced.map((price) => price.low)),
    });
  }
  return candles;
}

/** Daily (first open → last close) change per symbol over the most recent
 * trading day in the given states - the latest calendar day that has any
 * prices (on weekends/holidays that's the last session; before market open
 * it's the previous day). */
export function mapStatesToDailyChanges(
  states: readonly MarketStateResponseDto[],
): Record<string, PriceChange> {
  const opensByDay = new Map<string, Map<string, number>>();
  const closesByDay = new Map<string, Map<string, number>>();
  for (const state of states) {
    for (const price of Object.values(state.prices)) {
      const opens = opensByDay.get(state.hour.day) ?? new Map<string, number>();
      const closes = closesByDay.get(state.hour.day) ?? new Map<string, number>();
      if (!opens.has(price.symbol)) opens.set(price.symbol, price.open);
      closes.set(price.symbol, price.close);
      opensByDay.set(state.hour.day, opens);
      closesByDay.set(state.hour.day, closes);
    }
  }
  // ISO day keys sort chronologically.
  const dayKeys = [...opensByDay.keys()].sort();
  const latestDay = dayKeys[dayKeys.length - 1];
  const opens = latestDay != null ? opensByDay.get(latestDay) : undefined;
  const closes = latestDay != null ? closesByDay.get(latestDay) : undefined;
  if (latestDay == null || opens == null || closes == null) return {};

  const changes: Record<string, PriceChange> = {};
  for (const [symbol, open] of opens) {
    const close = closes.get(symbol) ?? open;
    const abs = close - open;
    changes[symbol] = { abs, pct: open !== 0 ? (abs / open) * 100 : 0 };
  }
  return changes;
}

/* -------------------------------------------------------------------------- */
/* Portfolio                                                                   */
/* -------------------------------------------------------------------------- */

export interface PortfolioOverview {
  cash: number;
  holdings: Holding[];
  /** Cash plus holdings valued at their last prices. */
  value: number;
}

export function mapPortfolioOverview(
  portfolio: PortfolioResponseDto,
  lastPrices: Record<string, number>,
): PortfolioOverview {
  const holdings: Holding[] = Object.entries(portfolio.holdings).map(([symbol, shares]) => ({
    symbol,
    shares,
    lastPrice: lastPrices[symbol] ?? 0,
  }));
  holdings.sort((first, second) => first.symbol.localeCompare(second.symbol));
  const holdingsValue = holdings.reduce(
    (sum, holding) => sum + holding.shares * holding.lastPrice,
    0,
  );
  return { cash: portfolio.cash, holdings, value: portfolio.cash + holdingsValue };
}

/**
 * Portfolio-value series from the recorded hourly states, with the live
 * value appended so the chart ends at the hero value. Padded to two points
 * when there's no history yet (e.g. a brand-new player), so the chart has a
 * line to draw.
 */
export function mapPortfolioHistoryToSeries(
  states: readonly PortfolioStateResponseDto[],
  currentValue: number,
): number[] {
  const series = states.map((state) => state.total_value);
  series.push(currentValue);
  if (series.length < 2) series.unshift(series[0]);
  return series;
}

/* -------------------------------------------------------------------------- */
/* Trades                                                                      */
/* -------------------------------------------------------------------------- */

/** Split a backend trade kind ("limit_buy") into UI type + side. */
function splitTradeKind(kind: TradeKindDto): { type: OrderType; side: OrderSide } {
  const [type, side] = kind.split("_") as [OrderType, OrderSide];
  return { type, side };
}

function joinTradeKind(type: OrderType, side: OrderSide): TradeKindDto {
  return `${type}_${side}` as TradeKindDto;
}

/** Map an unsent draft order to the backend's trade input shape. */
export function mapDraftToTradeInput(draft: NewOrder): TradeInputDto {
  const input: TradeInputDto = {
    symbol: draft.symbol,
    kind: joinTradeKind(draft.type, draft.side),
  };
  if ("shares" in draft.quantity) input.quantity = draft.quantity.shares;
  else input.value = draft.quantity.value;
  if (draft.type !== "market" && draft.price != null) input.requested_price = draft.price;
  return input;
}

export function mapActiveTradeToOpenOrder(dto: ActiveTradeDto): OpenOrder {
  const { type, side } = splitTradeKind(dto.kind);
  const quantity: OrderQuantity =
    dto.quantity != null ? { shares: dto.quantity } : { value: dto.value ?? 0 };
  return {
    id: dto.id,
    side,
    type,
    symbol: dto.symbol,
    quantity,
    price: dto.requested_price ?? undefined,
  };
}

const STATUS_BY_DTO: Record<InactiveTradeStatusDto, OrderStatus> = {
  executed: "filled",
  cancelled: "cancelled",
  error: "error",
  malformed_request: "error",
  insufficient_funds: "no_funds",
  symbol_unavailable: "delisted",
};

const STATUS_LABELS: Record<OrderStatus, string> = {
  filled: "Filled",
  cancelled: "Cancelled",
  error: "Error",
  no_funds: "No funds",
  delisted: "Delisted",
};

const REASONS_BY_STATUS: Record<OrderStatus, string | null> = {
  filled: null,
  cancelled: "You cancelled this order before it could fill.",
  error: "Execution failed due to a technical error — nothing was charged.",
  no_funds: "There wasn't enough buying power to execute this order.",
  delisted: "The symbol stopped trading before this order could fill.",
};

/** Group closed trades by the day they were closed, most recent day first. */
export function mapClosedTradesToHistory(closed: readonly HistoricalTradeDto[]): HistoryDay[] {
  const ordersByDay = new Map<string, HistoryOrder[]>();
  for (const dto of closed) {
    const dayOrders = ordersByDay.get(dto.closed_at_hour.day) ?? [];
    dayOrders.push(mapClosedTradeToHistoryOrder(dto));
    ordersByDay.set(dto.closed_at_hour.day, dayOrders);
  }
  return [...ordersByDay.entries()]
    .sort(([firstDay], [secondDay]) => (firstDay < secondDay ? 1 : -1))
    .map(([day, orders]) => ({ date: formatDayLabel(day), orders }));
}

function mapClosedTradeToHistoryOrder(dto: HistoricalTradeDto): HistoryOrder {
  const status = STATUS_BY_DTO[dto.status];
  const { type, side } = splitTradeKind(dto.kind);
  return {
    id: dto.id,
    status,
    label: buildHistoryLabel(dto, side),
    details: buildOrderDetails(dto, type, side, status),
  };
}

function buildHistoryLabel(dto: HistoricalTradeDto, side: OrderSide): string {
  const sideLabel = side.toUpperCase();
  const quantity = quantityLabel(dto);
  if (dto.status === "executed" && dto.fill_price != null) {
    return `${sideLabel} ${quantity} @ ${dto.fill_price.toFixed(2)}`;
  }
  const { type } = splitTradeKind(dto.kind);
  return `${type.toUpperCase()} ${sideLabel} ${quantity}`;
}

function buildOrderDetails(
  dto: HistoricalTradeDto,
  type: OrderType,
  side: OrderSide,
  status: OrderStatus,
): OrderDetails {
  const typeLabel = capitalize(type);
  const fields: OrderDetailField[] = [
    { label: "Type", value: `${typeLabel} ${side}` },
    { label: "Symbol", value: dto.symbol },
    { label: "Requested", value: requestedLabel(dto) },
  ];
  if (type !== "market" && dto.requested_price != null) {
    fields.push({
      label: type === "limit" ? "Limit price" : "Stop price",
      value: `$${dto.requested_price.toFixed(2)}`,
    });
  }
  if (dto.status === "executed" && dto.fill_price != null) {
    fields.push({ label: "Fill price", value: `$${dto.fill_price.toFixed(2)}` });
  }
  if (status !== "filled") {
    fields.push({ label: "Status", value: STATUS_LABELS[status] });
  }
  fields.push({
    label: status === "filled" ? "Filled at" : "Closed at",
    value: formatHourLabel(dto.closed_at_hour),
  });
  return {
    status,
    title: `${typeLabel} ${side} · ${dto.symbol}`,
    reason: REASONS_BY_STATUS[status],
    fields,
  };
}

/** "60 HLIX" for share quantities, "$1,750 ORCA" for dollar quantities. */
function quantityLabel(dto: HistoricalTradeDto | ActiveTradeDto): string {
  const amount =
    dto.quantity != null ? formatShares(dto.quantity) : formatWholeUsd(dto.value ?? 0);
  return `${amount} ${dto.symbol}`;
}

function requestedLabel(dto: HistoricalTradeDto | ActiveTradeDto): string {
  if (dto.quantity != null) return `${formatShares(dto.quantity)} shares`;
  if (dto.value != null) return `${formatWholeUsd(dto.value)} of stock`;
  return "—";
}

/** "11:00 · Sep 11" from the backend's hourly date. */
function formatHourLabel(hour: HourlyDateDto): string {
  const hourText = String(hour.hour).padStart(2, "0");
  return `${hourText}:00 · ${formatDayLabel(hour.day)}`;
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
