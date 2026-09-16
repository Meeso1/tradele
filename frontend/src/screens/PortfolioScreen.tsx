import { useState } from "react";

import { AppHeader } from "../components/AppHeader";
import { DetailsSheet } from "../components/DetailsSheet";
import { HistoryList } from "../components/HistoryList";
import { HoldingsList } from "../components/HoldingsList";
import { OpenOrdersList } from "../components/OpenOrdersList";
import { PortfolioSummary } from "../components/PortfolioSummary";
import { TabBar } from "../components/TabBar";
import { INITIAL_OPEN_ORDERS } from "../mock/data";
import type { OrderDetails, Tab } from "../types";
import styles from "./PortfolioScreen.module.css";

interface PortfolioScreenProps {
  onTabChange: (tab: Tab) => void;
}

export function PortfolioScreen({ onTabChange }: PortfolioScreenProps) {
  const [details, setDetails] = useState<OrderDetails | null>(null);

  return (
    <div className={styles.screen}>
      <AppHeader />

      <div className={styles.content}>
        <div className={styles.columns}>
          <div className={styles.primary}>
            <PortfolioSummary />
            <HoldingsList />
          </div>
          <div className={styles.secondary}>
            <OpenOrdersList orders={INITIAL_OPEN_ORDERS} onManage={() => onTabChange("market")} />
            <HistoryList onSelectOrder={setDetails} />
          </div>
        </div>
        <div className={styles.bottomSpacer} />
      </div>

      <div className={styles.footer}>
        <TabBar active="portfolio" onChange={onTabChange} />
      </div>

      {details && <DetailsSheet order={details} onClose={() => setDetails(null)} />}
    </div>
  );
}
