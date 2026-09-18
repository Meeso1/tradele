import type { Holding, NewOrder, SymbolQuote } from "../types";
import { formatShares, formatWholeUsd } from "../utils/format";
import { estimateCost, estimateShares, heldShares } from "../utils/orderMath";
import styles from "./MayNotFillWarning.module.css";

interface MayNotFillWarningProps {
  drafts: readonly NewOrder[];
  holdings: readonly Holding[];
  quotes: readonly SymbolQuote[];
  /** Cash currently available (buy drafts costing more may not fill). */
  cash: number;
  onDismiss: () => void;
}

/**
 * May-not-fill warning, shown for the first draft that may not fill: a sell
 * exceeding the shares currently held, or a buy costing more than the cash
 * on hand; renders nothing when no draft triggers either case.
 */
export function MayNotFillWarning({
  drafts,
  holdings,
  quotes,
  cash,
  onDismiss,
}: MayNotFillWarningProps) {
  const priceFor = (symbol: string): number | undefined =>
    quotes.find((candidate) => candidate.symbol === symbol)?.price;

  const overSell = drafts
    .filter((draft) => draft.side === "sell")
    .map((draft) => ({
      draft,
      held: heldShares(holdings, draft.symbol),
      selling: estimateShares(draft.quantity, priceFor(draft.symbol)),
    }))
    .find(({ held, selling }) => selling != null && selling > held);

  const overBudget =
    overSell == null
      ? drafts
          .filter((draft) => draft.side === "buy")
          .map((draft) => ({
            draft,
            cost: estimateCost(draft.quantity, priceFor(draft.symbol)),
          }))
          .find(({ cost }) => cost != null && cost > cash)
      : null;

  let text: string | null = null;
  if (overSell != null && overSell.selling != null) {
    text =
      `May not fill — you hold ${overSell.held} of ${formatShares(overSell.selling)} ` +
      `${overSell.draft.symbol} right now. Another order can free up shares first.`;
  } else if (overBudget != null && overBudget.cost != null) {
    text =
      `May not fill — you have ${formatWholeUsd(cash)} to spend and this ` +
      `${overBudget.draft.symbol} order needs about ${formatWholeUsd(overBudget.cost)}. ` +
      `Another order can free up cash first.`;
  }

  if (text == null) return null;

  return (
    <div className={styles.warn}>
      <span className={styles.warnIcon}>&#9888;</span>
      <span className={styles.warnText}>{text}</span>
      <button
        type="button"
        className={styles.warnClose}
        onClick={onDismiss}
        aria-label="Dismiss warning"
      >
        &times;
      </button>
    </div>
  );
}
