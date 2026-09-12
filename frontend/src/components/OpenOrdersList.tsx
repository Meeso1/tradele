import type { OpenOrder } from "../types";
import { orderQtyLabel, orderTypeLabel } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import { SideBadge } from "./SideBadge";
import styles from "./OpenOrdersList.module.css";

interface OpenOrdersListProps {
  orders: readonly OpenOrder[];
  /** Switch to the Market tab, where open orders can be cancelled. */
  onManage: () => void;
}

/** Read-only mirror of the market's open orders (Portfolio screen). */
export function OpenOrdersList({ orders, onManage }: OpenOrdersListProps) {
  return (
    <section>
      <div className={styles.head}>
        <SectionTitle>Open orders</SectionTitle>
        <button type="button" className={styles.manageLink} onClick={onManage}>
          Manage in Market &rarr;
        </button>
      </div>
      {orders.map((order) => (
        <div key={order.id} className={styles.row}>
          <SideBadge side={order.side} />
          <div className={styles.body}>
            <div className={styles.title}>
              {orderTypeLabel(order.type)} &middot; {order.symbol}
            </div>
            <div className={styles.meta}>
              {orderQtyLabel(order.quantity, order.price)} &middot; working
            </div>
          </div>
        </div>
      ))}
    </section>
  );
}
