import { useState } from "react";

import { useDayInfo } from "../hooks/useDayInfo";
import { metadataService } from "../services/MetadataService";
import styles from "./TutorialPopup.module.css";

/**
 * First-visit tutorial popup, driven by the backend's tutorial flag
 * (`/metadata`). Completing it (the "Got it" button or tapping the backdrop)
 * marks the tutorial done server-side so it never shows again.
 */
export function TutorialPopup() {
  const dayInfo = useDayInfo();
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || dayInfo.data == null || dayInfo.data.hasCompletedTutorial) return null;

  const complete = () => {
    setDismissed(true);
    // Fire-and-forget: if the request fails the popup simply reappears on
    // the next visit, since the server-side flag was never set.
    metadataService.completeTutorial().catch(() => {});
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.backdrop} onClick={complete} />
      <div className={styles.card} role="dialog" aria-modal="true" aria-label="Welcome to Tradele">
        <div className={styles.title}>Welcome to Tradele</div>
        <p className={styles.intro}>
          A daily game of market guesses — grow your portfolio one day at a time.
        </p>
        <ul className={styles.rules}>
          <li>One submission a day: new orders and cancellations go out together as a single set.</li>
          <li>Orders execute on the hour, at that hour's prices.</li>
          <li>Market, limit, and stop orders — buy by share count or dollar value.</li>
        </ul>
        <p className={styles.soon}>More fun features coming soon.</p>
        <button type="button" className={styles.done} onClick={complete}>
          Got it
        </button>
      </div>
    </div>
  );
}
