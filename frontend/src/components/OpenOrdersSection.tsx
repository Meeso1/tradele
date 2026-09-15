import type { OpenOrderState } from "../types";
import { orderQtyLabel, orderTypeLabel } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import { SideBadge } from "./SideBadge";
import styles from "./OpenOrdersSection.module.css";

interface OpenOrdersSectionProps {
  entries: readonly OpenOrderState[];
  /** After the daily submission the book is locked - no cancels until tomorrow. */
  locked: boolean;
  /** Mark an order as cancelling (or undo the cancellation). */
  onSetCancel: (id: string, cancelling: boolean) => void;
}

/** Open orders with cancel/undo actions (Market screen). */
export function OpenOrdersSection({ entries, locked, onSetCancel }: OpenOrdersSectionProps) {
  return (
    <section>
      <div className={styles.sectionHead}>
        <SectionTitle>Open orders</SectionTitle>
        {!locked && <div className={styles.sectionNote}>cancel only</div>}
      </div>
      {entries.map((entry) => {
        const order = entry.order;
        return (
          <div
            key={order.id}
            className={entry.cancelling ? styles.orderCardCancelling : styles.orderCard}
          >
            <SideBadge side={order.side} />
            <div className={styles.orderBody}>
              <div className={entry.cancelling ? styles.orderTitleCancelled : styles.orderTitle}>
                {orderTypeLabel(order.type)} &middot; {order.symbol}
              </div>
              {entry.cancelling ? (
                <div className={styles.orderMetaDown}>will cancel on submit</div>
              ) : (
                <div className={styles.orderMeta}>
                  {orderQtyLabel(order.quantity, order.price)} &middot; working
                </div>
              )}
            </div>
            {!locked &&
              (entry.cancelling ? (
                <button
                  type="button"
                  className={styles.undoBtn}
                  onClick={() => onSetCancel(order.id, false)}
                >
                  Undo
                </button>
              ) : (
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => onSetCancel(order.id, true)}
                >
                  Cancel
                </button>
              ))}
          </div>
        );
      })}
    </section>
  );
}
