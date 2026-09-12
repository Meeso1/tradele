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

/** Open orders with their cancelling flags; submitting applies cancellations. */
function useOpenOrders() {
  const [entries, setEntries] = useState(INITIAL_OPEN_ORDER_STATES);

  const cancelCount = entries.filter((entry) => entry.cancelling).length;
  const setCancel = (id: string, cancelling: boolean) => {
    setEntries((prev) =>
      prev.map((entry) => (entry.order.id === id ? { ...entry, cancelling } : entry)),
    );
  };
  const applySubmit = () => setEntries((prev) => prev.filter((entry) => !entry.cancelling));

  return { entries, cancelCount, setCancel, applySubmit };
}

/** Order builder + drafted orders ("New today" set) as one cohesive unit. */
function useDraftBuilder(symbol: string, onSelectSymbol: (symbol: string) => void) {
  const [builderOpen, setBuilderOpen] = useState(true);
  const [editing, setEditing] = useState<{ key: number; draft: DraftOrderInput } | null>(null);
  const [drafts, setDrafts] = useState<NewOrder[]>(INITIAL_NEW_ORDERS);
  const [submitted, setSubmitted] = useState(false);

  const addDraft = (draft: DraftOrderInput) => {
    setSubmitted(false);
    setDrafts((prev) => [...prev, { id: `nt-${nextDraftId++}`, symbol, ...draft }]);
  };

  const removeDraft = (id: string) => {
    setSubmitted(false);
    setDrafts((prev) => prev.filter((draft) => draft.id !== id));
  };

  const editDraft = (draft: NewOrder) => {
    // Mock: editing pulls the draft back into the builder (remounted via key).
    removeDraft(draft.id);
    onSelectSymbol(draft.symbol);
    setEditing({ key: Date.now(), draft: { ...draft } });
    setBuilderOpen(true);
  };

  /** Clears the set on submit; drafts added afterwards start a fresh set. */
  const clear = () => {
    setDrafts([]);
    setSubmitted(true);
  };

  return {
    builderOpen,
    setBuilderOpen,
    editing,
    drafts,
    submitted,
    addDraft,
    removeDraft,
    editDraft,
    clear,
  };
}

export function MarketScreen({ onTabChange }: MarketScreenProps) {
  const [selectedSymbol, setSelectedSymbol] = useState(QUOTES[0].symbol);
  const quote =
    QUOTES.find((candidate) => candidate.symbol === selectedSymbol) ?? QUOTES[0];
  const { entries, cancelCount, setCancel, applySubmit } = useOpenOrders();
  const {
    builderOpen,
    setBuilderOpen,
    editing,
    drafts,
    submitted,
    addDraft,
    removeDraft,
    editDraft,
    clear,
  } = useDraftBuilder(selectedSymbol, setSelectedSymbol);
  const [warnDismissed, setWarnDismissed] = useState(false);

  const submit = () => {
    applySubmit();
    clear();
    setWarnDismissed(false);
  };

  return (
    <div className={styles.screen}>
      <AppHeader showMarketStatus />

      <div className={styles.content}>
        <TickerStrip selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
        <QuoteDetail quote={quote} />
        <OrderBuilder
          key={editing?.key ?? "fresh"}
          quote={quote}
          buyingPower={BUYING_POWER}
          open={builderOpen}
          onToggle={() => setBuilderOpen((prev) => !prev)}
          onAdd={addDraft}
          initial={editing?.draft}
        />
        <OpenOrdersSection entries={entries} onSetCancel={setCancel} />
        <NewTodaySection
          drafts={drafts}
          submitted={submitted}
          onEdit={editDraft}
          onRemove={removeDraft}
        />
        {!warnDismissed && (
          <MayNotFillWarning drafts={drafts} onDismiss={() => setWarnDismissed(true)} />
        )}
        <div className={styles.bottomSpacer} />
      </div>

      <div className={styles.footer}>
        <SubmitBar draftsCount={drafts.length} cancelCount={cancelCount} onSubmit={submit} />
        <TabBar active="market" onChange={onTabChange} />
      </div>
    </div>
  );
}
