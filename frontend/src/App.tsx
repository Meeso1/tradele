import { useState } from "react";

import { MarketScreen } from "./screens/MarketScreen";
import { PortfolioScreen } from "./screens/PortfolioScreen";
import type { Tab } from "./types";


export default function App() {
  const [tab, setTab] = useState<Tab>("market");

  return (
    <div className="shell">
      {tab === "market" ? (
        <MarketScreen onTabChange={setTab} />
      ) : (
        <PortfolioScreen onTabChange={setTab} />
      )}
    </div>
  );
}
