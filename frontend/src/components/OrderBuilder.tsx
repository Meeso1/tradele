import { useState } from "react";

import type { OrderQuantity, OrderSide, OrderType, QtyMode, SymbolQuote } from "../types";
import { formatWholeUsd } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import styles from "./OrderBuilder.module.css";

export interface DraftOrderInput {
  type: OrderType;
  side: OrderSide;
  quantity: OrderQuantity;
  price?: number;
}

interface OrderBuilderProps {
  quote: SymbolQuote;
  /** Cash available for buying-power percentages. */
  buyingPower: number;
  open: boolean;
  onToggle: () => void;
  onAdd: (draft: DraftOrderInput) => void;
  /** Prefills the form when editing an existing draft (remount via `key` to apply). */
  initial?: DraftOrderInput;
}

interface OrderTypeSpec {
  label: string;
  priceField?: { label: string; defaultFactor: number };
}

const ORDER_TYPE_SPECS: Record<OrderType, OrderTypeSpec> = {
  market: { label: "Market" },
  limit: { label: "Limit", priceField: { label: "Limit price", defaultFactor: 0.99 } },
  stop: { label: "Stop", priceField: { label: "Stop price", defaultFactor: 0.95 } },
};

const ORDER_TYPE_ORDER: OrderType[] = ["market", "limit", "stop"];

// TODO: multi-legged orders (more than a single buy/sell) would need per-leg
// sides and quantities; extend ORDER_TYPE_SPECS and the side model when that lands.

const SIDES: { id: OrderSide; label: string }[] = [
  { id: "buy", label: "Buy" },
  { id: "sell", label: "Sell" },
];

const PERCENTS = [25, 50, 75, 100] as const;
const DEFAULT_PERCENT = 50;

function sanitizeNumberText(raw: string): string {
  return raw.replace(/[^0-9.]/g, "");
}

export function OrderBuilder({ quote, buyingPower, open, onToggle, onAdd, initial }: OrderBuilderProps) {
  const [type, setType] = useState<OrderType>(initial?.type ?? "limit");
  const [side, setSide] = useState<OrderSide>(initial?.side ?? "buy");
  const [qtyMode, setQtyMode] = useState<QtyMode>(
    initial != null && "value" in initial.quantity ? "value" : "shares",
  );
  // Both quantities are stored and kept in agreement while typing (typing in
  // one writes the converted value into the other), so switching modes only
  // flips which one is shown and never mutates the entered number.
  const [sharesText, setSharesText] = useState<string>(() => {
    if (initial == null) {
      return ((DEFAULT_PERCENT / 100) * buyingPower / quote.price).toFixed(1);
    }
    if ("shares" in initial.quantity) return String(initial.quantity.shares);
    return (initial.quantity.value / quote.price).toFixed(1);
  });
  const [valueText, setValueText] = useState<string>(() => {
    if (initial == null) return ((DEFAULT_PERCENT / 100) * buyingPower).toFixed(0);
    if ("value" in initial.quantity) return String(initial.quantity.value);
    return (initial.quantity.shares * quote.price).toFixed(0);
  });
  const [activePercent, setActivePercent] = useState<number | null>(
    initial == null ? DEFAULT_PERCENT : null,
  );
  const [priceText, setPriceText] = useState<string>(
    initial?.price != null ? String(initial.price) : "",
  );

  const spec = ORDER_TYPE_SPECS[type];
  const amountText = qtyMode === "shares" ? sharesText : valueText;
  const amount = parseFloat(amountText);
  const amountValid = Number.isFinite(amount) && amount > 0;
  // Client-side conversions are for the "≈" hints only - the submitted quantity
  // stays in whichever unit the user entered.
  const shares = qtyMode === "shares" ? amount : amount / quote.price;
  const value = qtyMode === "shares" ? amount * quote.price : amount;

  const defaultPrice =
    spec.priceField != null
      ? Math.round(quote.price * spec.priceField.defaultFactor * 100) / 100
      : undefined;
  const effectivePrice =
    spec.priceField == null ? undefined : priceText !== "" ? parseFloat(priceText) : defaultPrice;
  const priceValid = spec.priceField == null || (effectivePrice != null && effectivePrice > 0);
  const canSubmit = amountValid && priceValid;

  const changeQtyMode = (mode: QtyMode) => {
    if (mode === qtyMode) return;
    setQtyMode(mode);
    setActivePercent(null);
  };

  const changeAmount = (raw: string) => {
    const sanitized = sanitizeNumberText(raw);
    setActivePercent(null);
    if (qtyMode === "shares") {
      setSharesText(sanitized);
      const parsed = parseFloat(sanitized);
      if (Number.isFinite(parsed) && parsed > 0) {
        setValueText((parsed * quote.price).toFixed(0));
      }
    } else {
      setValueText(sanitized);
      const parsed = parseFloat(sanitized);
      if (Number.isFinite(parsed) && parsed > 0) {
        setSharesText((parsed / quote.price).toFixed(1));
      }
    }
  };

  const applyPercent = (percent: number) => {
    setActivePercent(percent);
    const budget = (percent / 100) * buyingPower;
    setSharesText((budget / quote.price).toFixed(1));
    setValueText(budget.toFixed(0));
  };

  const submit = () => {
    if (!canSubmit) return;
    const quantity: OrderQuantity = qtyMode === "shares" ? { shares: amount } : { value: amount };
    onAdd({ type, side, quantity, price: effectivePrice });
  };

  const renderTypeFields = () => {
    if (spec.priceField == null) return null;
    return (
      <div className={styles.priceField}>
        <div className={styles.priceLabel}>{spec.priceField.label}</div>
        <div className={styles.priceBox}>
          <span className={styles.pricePrefix}>$</span>
          <input
            className={styles.priceInput}
            inputMode="decimal"
            aria-label={spec.priceField.label}
            placeholder={(defaultPrice ?? 0).toFixed(2)}
            value={priceText}
            onChange={(event) => setPriceText(sanitizeNumberText(event.target.value))}
          />
        </div>
      </div>
    );
  };

  return (
    <section>
      <button type="button" className={styles.header} onClick={onToggle}>
        <SectionTitle>New order</SectionTitle>
        {open ? (
          <span className={styles.headerChevron}>&#9662;</span>
        ) : (
          <span className={styles.headerAdd}>
            + Add<span className={styles.headerChevron}>&#9656;</span>
          </span>
        )}
      </button>

      {open && (
        <div className={styles.panel}>
          <div className={styles.typeTabs}>
            {ORDER_TYPE_ORDER.map((typeId) => (
              <button
                key={typeId}
                type="button"
                className={type === typeId ? styles.typeTabActive : styles.typeTab}
                onClick={() => setType(typeId)}
              >
                {ORDER_TYPE_SPECS[typeId].label}
              </button>
            ))}
          </div>

          <div className={styles.sides}>
            {SIDES.map((sideOption) => {
              const active = side === sideOption.id;
              const className = !active
                ? styles.side
                : sideOption.id === "buy"
                  ? styles.sideBuyActive
                  : styles.sideSellActive;
              return (
                <button
                  key={sideOption.id}
                  type="button"
                  className={className}
                  onClick={() => setSide(sideOption.id)}
                >
                  {sideOption.label}
                </button>
              );
            })}
          </div>

          <div className={styles.amountRow}>
            <div className={styles.amountLabel}>Amount</div>
            <div className={styles.modes}>
              <button
                type="button"
                className={qtyMode === "shares" ? styles.modeActive : styles.mode}
                onClick={() => changeQtyMode("shares")}
              >
                Shares
              </button>
              <button
                type="button"
                className={qtyMode === "value" ? styles.modeActive : styles.mode}
                onClick={() => changeQtyMode("value")}
              >
                Value
              </button>
            </div>
          </div>

          <div className={styles.qtyBox}>
            <span className={styles.qtyMain}>
              {qtyMode === "value" && <span className={styles.qtyPrefix}>$</span>}
              <input
                className={styles.qtyInput}
                inputMode="decimal"
                aria-label={qtyMode === "shares" ? "Shares" : "Dollar value"}
                value={amountText}
                onChange={(event) => changeAmount(event.target.value)}
              />
              {qtyMode === "shares" && <span className={styles.qtyUnit}>sh</span>}
            </span>
            {amountValid && (
              <span className={styles.qtyApprox}>
                &asymp;{" "}
                {qtyMode === "shares" ? formatWholeUsd(value) : `${shares.toFixed(2)} sh`}
              </span>
            )}
          </div>

          <div className={styles.percents}>
            {PERCENTS.map((percent) => (
              <button
                key={percent}
                type="button"
                className={activePercent === percent ? styles.percentActive : styles.percent}
                onClick={() => applyPercent(percent)}
              >
                {percent === 100 ? "Max" : `${percent}%`}
              </button>
            ))}
          </div>

          {renderTypeFields()}

          <button type="button" className={styles.addOrder} onClick={submit} disabled={!canSubmit}>
            Add order
          </button>
        </div>
      )}
    </section>
  );
}
