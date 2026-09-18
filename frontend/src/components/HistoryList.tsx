import type { HistoryDay, OrderDetails } from "../types";
import { SectionTitle } from "./SectionTitle";
import { StatusChip } from "./StatusChip";
import styles from "./HistoryList.module.css";

interface HistoryListProps {
  days: readonly HistoryDay[];
  onSelectOrder: (details: OrderDetails) => void;
}

/** Past days, each listing the trades that were closed during that day. */
export function HistoryList({ days, onSelectOrder }: HistoryListProps) {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>History</SectionTitle>
      </div>
      {days.map((day) => (
        <div key={day.date} className={styles.card}>
          <div className={styles.cardDate}>{day.date}</div>
          <div className={styles.cardOrders}>
            {day.orders.map((order) => (
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
      ))}
      {days.length === 0 && <div className={styles.emptyNote}>No closed trades yet.</div>}
    </section>
  );
}
