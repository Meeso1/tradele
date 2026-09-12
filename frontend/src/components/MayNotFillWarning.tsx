import { estimateShares, heldShares } from "../mock/data";
import type { NewOrder } from "../types";
import { formatShares } from "../utils/format";
import styles from "./MayNotFillWarning.module.css";

interface MayNotFillWarningProps {
  drafts: readonly NewOrder[];
  onDismiss: () => void;
}

/**
 * May-not-fill warning, shown when a sell draft exceeds the shares currently
 * held; renders nothing when there is no such draft.
 */
export function MayNotFillWarning({ drafts, onDismiss }: MayNotFillWarningProps) {
  const overSell = drafts
    .filter((draft) => draft.side === "sell")
    .map((draft) => ({
      draft,
      held: heldShares(draft.symbol),
      selling: estimateShares(draft.quantity, draft.symbol),
    }))
    .find(({ held, selling }) => selling != null && selling > held);

  if (overSell == null || overSell.selling == null) return null;

  return (
    <div className={styles.warn}>
      <span className={styles.warnIcon}>&#9888;</span>
      <span className={styles.warnText}>
        May not fill &mdash; you hold {overSell.held} of {formatShares(overSell.selling)}{" "}
        {overSell.draft.symbol} right now. Fine if another order frees shares first.
      </span>
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
