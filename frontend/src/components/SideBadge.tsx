import type { OrderSide } from "../types";
import styles from "./SideBadge.module.css";

export function SideBadge({ side }: { side: OrderSide }) {
  return <div className={side === "buy" ? styles.buy : styles.sell}>{side.toUpperCase()}</div>;
}
