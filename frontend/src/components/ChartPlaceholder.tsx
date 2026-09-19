import styles from "./ChartPlaceholder.module.css";

interface ChartPlaceholderProps {
  message: string;
}

/**
 * Skeleton standing in for a chart with no (or too little) data - same
 * aspect ratio as the SVG charts (680x280) so the layout doesn't shift.
 */
export function ChartPlaceholder({ message }: ChartPlaceholderProps) {
  return (
    <div className={styles.placeholder} role="status">
      <span className={styles.message}>{message}</span>
    </div>
  );
}
