import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import { MayNotFillWarning } from "../components/MayNotFillWarning";
import { NewTodaySection } from "../components/NewTodaySection";
import { OpenOrdersSection } from "../components/OpenOrdersSection";
import { OrderBuilder, type DraftOrderInput } from "../components/OrderBuilder";
import { QuoteDetail } from "../components/QuoteDetail";
import { StatusNote } from "../components/StatusNote";
import { SubmitBar } from "../components/SubmitBar";
import { TabBar } from "../components/TabBar";
import { TickerStrip } from "../components/TickerStrip";
import { useAsync } from "../hooks/useAsync";
import { useDailyChanges } from "../hooks/useDailyChanges";
import { usePortfolioOverview } from "../hooks/usePortfolioOverview";
import { useQuotes } from "../hooks/useQuotes";
import { useTimeframePrefetch } from "../hooks/useTimeframePrefetch";
import { useTrades } from "../hooks/useTrades";
import { tradesService } from "../services/TradesService";
import type { NewOrder, OpenOrderState, Tab } from "../types";
import styles from "./MarketScreen.module.css";

interface MarketScreenProps {
  onTabChange: (tab: Tab) => void;
}

let nextDraftId = 100;

/**
 * The day's order book: live open orders (loaded from the trades API),
 * unsubmitted local drafts, and the locked state after the daily submission.
 * Cancellations are local flags until the set is committed with the single
 * daily submission (new drafts + cancels).
 */
function useOrderBook(symbol: string, onSelectSymbol: (symbol: string) => void) {
  const trades = useTrades();
  const submittedToday = useAsync(() => tradesService.hasSubmittedToday(), []);
  const [builderOpen, setBuilderOpen] = useState(true);
  const [editing, setEditing] = useState<{ key: number; draft: DraftOrderInput } | null>(null);
  const [entries, setEntries] = useState<OpenOrderState[]>([]);
  const [drafts, setDrafts] = useState<NewOrder[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Mirror the server's open orders into local state (which carries the
  // transient `cancelling` flags); flags reset whenever the list refreshes.
  useEffect(() => {
    if (trades.data == null) return;
    setEntries(trades.data.openOrders.map((order) => ({ order, cancelling: false })));
  }, [trades.data]);

  const locked = submittedToday.data ?? false;
  const cancelCount = entries.filter((entry) => entry.cancelling).length;

  const setCancel = (id: string, cancelling: boolean) => {
    setEntries((prev) =>
      prev.map((entry) => (entry.order.id === id ? { ...entry, cancelling } : entry)),
    );
  };

  const addDraft = (draft: DraftOrderInput) => {
    setDrafts((prev) => [...prev, { id: `nt-${nextDraftId++}`, symbol, ...draft }]);
  };

  const removeDraft = (id: string) => {
    setDrafts((prev) => prev.filter((draft) => draft.id !== id));
  };

  const editDraft = (draft: NewOrder) => {
    // Editing pulls the draft back into the builder (remounted via key).
    removeDraft(draft.id);
    onSelectSymbol(draft.symbol);
    setEditing({ key: Date.now(), draft: { ...draft } });
    setBuilderOpen(true);
  };

  /**
   * The single daily submission: sends the drafts and pending cancellations
   * as one batch, then refreshes the order book and locks it.
   */
  const submit = async () => {
    const cancelIds = entries.filter((entry) => entry.cancelling).map((entry) => entry.order.id);
    if (submitting || (drafts.length === 0 && cancelIds.length === 0)) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await tradesService.submit(drafts, cancelIds);
      setDrafts([]);
      trades.reload();
      submittedToday.reload();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        // Already submitted today (e.g. another tab won the race): lock and
        // show the server's state instead of an error.
        setDrafts([]);
        trades.reload();
        submittedToday.reload();
      } else {
        setSubmitError(
          error instanceof Error ? error.message : "Submitting the order set failed",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return {
    builderOpen, setBuilderOpen, editing, entries, drafts, locked, cancelCount,
    submitting, submitError, setCancel, addDraft, removeDraft, editDraft, submit,
  };
}

export function MarketScreen({ onTabChange }: MarketScreenProps) {
  useTimeframePrefetch();
  const quotes = useQuotes();
  const overview = usePortfolioOverview();
  const quoteList = quotes.data ?? [];
  const dailyChanges = useDailyChanges();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const quote =
    quoteList.find((candidate) => candidate.symbol === selectedSymbol) ?? quoteList[0] ?? null;
  const {
    builderOpen, setBuilderOpen, editing, entries, drafts, locked, cancelCount,
    submitting, submitError, setCancel, addDraft, removeDraft, editDraft, submit,
  } = useOrderBook(quote?.symbol ?? "", setSelectedSymbol);
  const [warnDismissed, setWarnDismissed] = useState(false);

  return (
    <div className={styles.screen}>
      <AppHeader />

      <div className={styles.content}>
        <TickerStrip
          quotes={quoteList}
          changes={dailyChanges.data ?? {}}
          selectedSymbol={quote?.symbol ?? ""}
          onSelect={setSelectedSymbol}
        />
        <div className={styles.columns}>
          <div className={styles.primary}>
            {quote != null ? (
              <QuoteDetail quote={quote} />
            ) : quotes.data != null && quotes.data.length === 0 ? (
              <StatusNote
                tone="empty"
                message="No price data available — the market may be closed"
              />
            ) : (
              <StatusNote
                tone={quotes.error == null ? "loading" : "error"}
                message={quotes.error ?? undefined}
                onRetry={quotes.error == null ? undefined : quotes.reload}
              />
            )}
          </div>
          <div className={styles.secondary}>
            {locked ? (
              <div className={styles.lockedNote}>
                Order set submitted &mdash; a new one unlocks tomorrow.
              </div>
            ) : (
              quote != null && (
                <OrderBuilder
                  key={editing?.key ?? "fresh"}
                  quote={quote}
                  buyingPower={overview.data?.cash ?? 0}
                  open={builderOpen}
                  onToggle={() => setBuilderOpen((prev) => !prev)}
                  onAdd={addDraft}
                  initial={editing?.draft}
                />
              )
            )}
            <OpenOrdersSection entries={entries} locked={locked} onSetCancel={setCancel} />
            <NewTodaySection drafts={drafts} locked={locked} onEdit={editDraft} onRemove={removeDraft} />
            {!warnDismissed && overview.data != null && (
              <MayNotFillWarning
                drafts={drafts}
                holdings={overview.data.holdings}
                quotes={quoteList}
                cash={overview.data.cash}
                onDismiss={() => setWarnDismissed(true)}
              />
            )}
          </div>
        </div>
        <div className={styles.bottomSpacer} />
      </div>

      {submitError != null && <StatusNote tone="error" message={submitError} />}

      <div className={styles.footer}>
        <SubmitBar
          draftsCount={drafts.length}
          cancelCount={cancelCount}
          locked={locked}
          submitting={submitting}
          onSubmit={submit}
        />
        <TabBar active="market" onChange={onTabChange} />
      </div>
    </div>
  );
}
