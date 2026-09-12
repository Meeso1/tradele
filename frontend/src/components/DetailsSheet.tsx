import type { OrderDetails } from "../types";
import { StatusChip } from "./StatusChip";
import styles from "./DetailsSheet.module.css";

interface DetailsSheetProps {
  order: OrderDetails;
  onClose: () => void;
}

/** Bottom sheet showing the full details of a past order. */
export function DetailsSheet({ order, onClose }: DetailsSheetProps) {
  return (
    <div className={styles.overlay}>
      <div className={styles.backdrop} onClick={onClose} />
      <div className={styles.sheet} role="dialog" aria-modal="true" aria-label={order.title}>
        <div className={styles.grabber} />
        <div className={styles.titleRow}>
          <StatusChip status={order.status} variant="soft" />
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <div className={styles.title}>{order.title}</div>
        {order.fields.map((field) => (
          <div key={field.label} className={styles.field}>
            <span className={styles.fieldKey}>{field.label}</span>
            <span className={styles.fieldValue}>{field.value}</span>
          </div>
        ))}
        {order.reason && <div className={styles.reason}>{order.reason}</div>}
      </div>
    </div>
  );
}
