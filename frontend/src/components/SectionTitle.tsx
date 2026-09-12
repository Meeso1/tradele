import type { ReactNode } from "react";

import styles from "./SectionTitle.module.css";

/** Uppercase mono section heading used across screens and panels. */
export function SectionTitle({ children }: { children: ReactNode }) {
  return <span className={styles.title}>{children}</span>;
}
