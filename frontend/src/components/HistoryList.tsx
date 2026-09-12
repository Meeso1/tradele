import { HISTORY } from "../mock/data";
import type { HistorySetState, OrderDetails } from "../types";
import { formatSignedUsd } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import { StatusChip } from "./StatusChip";
import styles from "./HistoryList.module.css";

interface HistoryListProps {
  onSelectOrder: (details: OrderDetails) => void;
}

// View state derived from the data: sets without (expandable) orders render as
// compact summary rows.
const SET_STATES: HistorySetState[] = HISTORY.map((set) => ({
  set,
  collapsed: set.orders.length === 0,
}));

/** Past daily order sets; tapping an order opens the details sheet. */
export function HistoryList({ onSelectOrder }: HistoryListProps) {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>History</SectionTitle>
      </div>
      {SET_STATES.map(({ set, collapsed }) => {
        if (collapsed) {
          return (
            <div key={set.id} className={styles.collapsedRow}>
              <div className={styles.collapsedId}>
                {set.id} &middot; {set.date}
              </div>
              <div className={set.pnl >= 0 ? styles.pnlUp : styles.pnlDown}>
                {formatSignedUsd(set.pnl)}
              </div>
            </div>
          );
        }
        const highlighted = set.changesSinceSubmit != null;
        return (
          <div key={set.id} className={highlighted ? styles.cardHl : styles.card}>
            <div className={styles.cardHead}>
              <div className={highlighted ? styles.cardId : styles.cardIdMuted}>
                {set.id} &middot; {set.date}
              </div>
              <div className={set.pnl >= 0 ? styles.pnlUp : styles.pnlDown}>
                {formatSignedUsd(set.pnl)}
              </div>
            </div>
            {highlighted && (
              <div className={styles.changesRow}>
                <span className={styles.changesDot} />
                {set.changesSinceSubmit} changes since your last submit
              </div>
            )}
            <div className={styles.cardOrders}>
              {set.orders.map((order) => (
                <button
                  key={order.id}
                  type="button"
                  className={order.status === "cancelled" ? styles.orderRowMuted : styles.orderRow}
                  onClick={() => onSelectOrder(order.details)}
                >
                  <StatusChip status={order.status} />
                  <span
                    className={
                      order.status === "cancelled" ? styles.orderLabelStrike : styles.orderLabel
                    }
                  >
                    {order.label}
                  </span>
                  <span className={styles.orderChevron}>&#9656;</span>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </section>
  );
}
