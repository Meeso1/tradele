import { useState } from "react";

import { AppHeader } from "../components/AppHeader";
import { DetailsSheet } from "../components/DetailsSheet";
import { HistoryList } from "../components/HistoryList";
import { HoldingsList } from "../components/HoldingsList";
import { OpenOrdersList } from "../components/OpenOrdersList";
import { PortfolioSummary } from "../components/PortfolioSummary";
import { StatusNote } from "../components/StatusNote";
import { TabBar } from "../components/TabBar";
import { usePortfolioOverview } from "../hooks/usePortfolioOverview";
import { useTrades } from "../hooks/useTrades";
import type { OrderDetails, Tab } from "../types";
import styles from "./PortfolioScreen.module.css";

interface PortfolioScreenProps {
  onTabChange: (tab: Tab) => void;
}

export function PortfolioScreen({ onTabChange }: PortfolioScreenProps) {
  const overview = usePortfolioOverview();
  const trades = useTrades();
  const [details, setDetails] = useState<OrderDetails | null>(null);

  return (
    <div className={styles.screen}>
      <AppHeader />

      <div className={styles.content}>
        <div className={styles.columns}>
          <div className={styles.primary}>
            <PortfolioSummary overview={overview.data} />
            {overview.data != null && (
              <HoldingsList holdings={overview.data.holdings} cash={overview.data.cash} />
            )}
            {overview.error != null && (
              <StatusNote tone="error" message={overview.error} onRetry={overview.reload} />
            )}
          </div>
          <div className={styles.secondary}>
            <OpenOrdersList
              orders={trades.data?.openOrders ?? []}
              onManage={() => onTabChange("market")}
            />
            <HistoryList days={trades.data?.history ?? []} onSelectOrder={setDetails} />
            {trades.error != null && (
              <StatusNote tone="error" message={trades.error} onRetry={trades.reload} />
            )}
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
