import type { Tab } from "../types";
import styles from "./TabBar.module.css";

interface TabBarProps {
  active: Tab;
  onChange: (tab: Tab) => void;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "market", label: "Market" },
  { id: "portfolio", label: "Portfolio" },
];

export function TabBar({ active, onChange }: TabBarProps) {
  return (
    <nav className={styles.bar}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={tab.id === active ? styles.tabActive : styles.tab}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
