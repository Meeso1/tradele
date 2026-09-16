import { useState } from "react";

import { AppHeader } from "../components/AppHeader";
import { MayNotFillWarning } from "../components/MayNotFillWarning";
import { NewTodaySection } from "../components/NewTodaySection";
import { OpenOrdersSection } from "../components/OpenOrdersSection";
import { OrderBuilder, type DraftOrderInput } from "../components/OrderBuilder";
import { QuoteDetail } from "../components/QuoteDetail";
import { SubmitBar } from "../components/SubmitBar";
import { TabBar } from "../components/TabBar";
import { TickerStrip } from "../components/TickerStrip";
import { BUYING_POWER, INITIAL_NEW_ORDERS, INITIAL_OPEN_ORDERS, QUOTES } from "../mock/data";
import type { NewOrder, OpenOrderState, Tab } from "../types";
import styles from "./MarketScreen.module.css";

interface MarketScreenProps {
  onTabChange: (tab: Tab) => void;
}

let nextDraftId = 100;

const INITIAL_OPEN_ORDER_STATES: OpenOrderState[] = INITIAL_OPEN_ORDERS.map((order) => ({
  order,
  cancelling: false,
}));

/**
 * The day's order book: live open orders, unsubmitted drafts, and the locked
 * state after the daily submission. Cancellations are local flags until the
 * set is committed with the single daily submission (new drafts + cancels).
 */
function useOrderBook(symbol: string, onSelectSymbol: (symbol: string) => void) {
  const [builderOpen, setBuilderOpen] = useState(true);
  const [editing, setEditing] = useState<{ key: number; draft: DraftOrderInput } | null>(null);
  const [entries, setEntries] = useState(INITIAL_OPEN_ORDER_STATES);
  const [drafts, setDrafts] = useState<NewOrder[]>(INITIAL_NEW_ORDERS);
  const [locked, setLocked] = useState(false);

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
    // Mock: editing pulls the draft back into the builder (remounted via key).
    removeDraft(draft.id);
    onSelectSymbol(draft.symbol);
    setEditing({ key: Date.now(), draft: { ...draft } });
    setBuilderOpen(true);
  };

  /**
   * The single daily submission: promotes drafts to working orders, applies
   * the pending cancellations, and locks the book until the next day.
   */
  const submit = () => {
    setEntries((prev) => [
      ...prev.filter((entry) => !entry.cancelling),
      ...drafts.map((draft) => ({ order: draft, cancelling: false })),
    ]);
    setDrafts([]);
    setLocked(true);
  };

  return {
    builderOpen, setBuilderOpen, editing, entries, drafts, locked, cancelCount,
    setCancel, addDraft, removeDraft, editDraft, submit,
  };
}

export function MarketScreen({ onTabChange }: MarketScreenProps) {
  const [selectedSymbol, setSelectedSymbol] = useState(QUOTES[0].symbol);
  const quote =
    QUOTES.find((candidate) => candidate.symbol === selectedSymbol) ?? QUOTES[0];
  const {
    builderOpen, setBuilderOpen, editing, entries, drafts, locked, cancelCount,
    setCancel, addDraft, removeDraft, editDraft, submit: commitOrderSet,
  } = useOrderBook(selectedSymbol, setSelectedSymbol);
  const [warnDismissed, setWarnDismissed] = useState(false);

  const submit = () => {
    commitOrderSet();
    setWarnDismissed(false);
  };

  return (
    <div className={styles.screen}>
      <AppHeader />

      <div className={styles.content}>
        <TickerStrip selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
        <div className={styles.columns}>
          <div className={styles.primary}>
            <QuoteDetail quote={quote} />
          </div>
          <div className={styles.secondary}>
            {locked ? (
              <div className={styles.lockedNote}>
                Order set submitted &mdash; a new one unlocks tomorrow.
              </div>
            ) : (
              <OrderBuilder
                key={editing?.key ?? "fresh"}
                quote={quote}
                buyingPower={BUYING_POWER}
                open={builderOpen}
                onToggle={() => setBuilderOpen((prev) => !prev)}
                onAdd={addDraft}
                initial={editing?.draft}
              />
            )}
            <OpenOrdersSection entries={entries} locked={locked} onSetCancel={setCancel} />
            <NewTodaySection drafts={drafts} locked={locked} onEdit={editDraft} onRemove={removeDraft} />
            {!warnDismissed && (
              <MayNotFillWarning drafts={drafts} onDismiss={() => setWarnDismissed(true)} />
            )}
          </div>
        </div>
        <div className={styles.bottomSpacer} />
      </div>

      <div className={styles.footer}>
        <SubmitBar
          draftsCount={drafts.length}
          cancelCount={cancelCount}
          locked={locked}
          onSubmit={submit}
        />
        <TabBar active="market" onChange={onTabChange} />
      </div>
    </div>
  );
}
