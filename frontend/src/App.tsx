import { useEffect, useState } from "react";

import { ensureSession } from "./api/client";
import { StatusNote } from "./components/StatusNote";
import { MarketScreen } from "./screens/MarketScreen";
import { PortfolioScreen } from "./screens/PortfolioScreen";
import type { Tab } from "./types";

type SessionState =
  | { status: "pending" }
  | { status: "ready" }
  | { status: "error"; message: string };

export default function App() {
  const [tab, setTab] = useState<Tab>("market");
  const [session, setSession] = useState<SessionState>({ status: "pending" });
  const [attempt, setAttempt] = useState(0);

  // Every API endpoint requires a token, so bootstrap the anonymous session
  // (create a user + mint a token on first visit) before showing any screen.
  useEffect(() => {
    let cancelled = false;
    setSession({ status: "pending" });
    ensureSession()
      .then(() => {
        if (!cancelled) setSession({ status: "ready" });
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setSession({
          status: "error",
          message: cause instanceof Error ? cause.message : "Could not reach the server",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  if (session.status !== "ready") {
    return (
      <div className="shell">
        <StatusNote
          tone={session.status === "error" ? "error" : "loading"}
          message={session.status === "error" ? session.message : "Connecting\u2026"}
          onRetry={
            session.status === "error"
              ? () => setAttempt((previous) => previous + 1)
              : undefined
          }
        />
      </div>
    );
  }

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
