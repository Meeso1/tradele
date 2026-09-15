import { HISTORY } from "../mock/data";
import type { HistoryDay, OrderDetails } from "../types";
import { SectionTitle } from "./SectionTitle";
import { StatusChip } from "./StatusChip";
import styles from "./HistoryList.module.css";

interface HistoryListProps {
  onSelectOrder: (details: OrderDetails) => void;
}

/** Past days, each listing the trades that were closed during that day. */
export function HistoryList({ onSelectOrder }: HistoryListProps) {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>History</SectionTitle>
      </div>
      {HISTORY.map((day: HistoryDay) => (
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
    </section>
  );
}
