import type { NewOrder } from "../types";
import { orderQtyLabel, orderTypeLabel } from "../utils/format";
import { SectionTitle } from "./SectionTitle";
import { SideBadge } from "./SideBadge";
import styles from "./NewTodaySection.module.css";

interface NewTodaySectionProps {
  drafts: readonly NewOrder[];
  /** Show the "submitted" empty-state message instead of "no drafts yet". */
  submitted: boolean;
  onEdit: (draft: NewOrder) => void;
  onRemove: (id: string) => void;
}

/** Drafted orders for today's set, with edit/remove actions. */
export function NewTodaySection({
  drafts,
  submitted,
  onEdit,
  onRemove,
}: NewTodaySectionProps) {
  return (
    <section>
      <div className={styles.sectionHeadPlain}>
        <SectionTitle>New today</SectionTitle>
      </div>
      {drafts.map((draft) => (
        <div key={draft.id} className={styles.draftCard}>
          <SideBadge side={draft.side} />
          <div className={styles.orderBody}>
            <div className={styles.orderTitle}>
              {orderTypeLabel(draft.type)} &middot; {draft.symbol}
            </div>
            <div className={styles.orderMeta}>{orderQtyLabel(draft.quantity, draft.price)}</div>
          </div>
          <div className={styles.draftActions}>
            <button type="button" className={styles.editLink} onClick={() => onEdit(draft)}>
              Edit
            </button>
            <button type="button" className={styles.removeLink} onClick={() => onRemove(draft.id)}>
              Remove
            </button>
          </div>
        </div>
      ))}
      {drafts.length === 0 && (
        <div className={styles.emptyNote}>
          {submitted ? "Order set submitted — see you tomorrow." : "No drafts yet."}
        </div>
      )}
    </section>
  );
}
