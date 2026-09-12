import type { OrderStatus } from "../types";
import styles from "./StatusChip.module.css";

const LABELS: Record<OrderStatus, string> = {
  filled: "FILLED",
  cancelled: "CANCELLED",
  no_funds: "NO FUNDS",
  delisted: "DELISTED",
};

interface StatusChipProps {
  status: OrderStatus;
  /** "solid" for history rows, "soft" (tinted background) for the details sheet. */
  variant?: "solid" | "soft";
}

export function StatusChip({ status, variant = "solid" }: StatusChipProps) {
  return (
    <span className={`${styles[variant]} ${styles[status]}`}>{LABELS[status]}</span>
  );
}
