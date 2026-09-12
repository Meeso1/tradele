/** Whole hours until the end of the current local day (at least 1). */
export function hoursUntilEndOfDay(): number {
  const now = new Date();
  const endOfDay = new Date(now);
  endOfDay.setHours(24, 0, 0, 0);
  const millisLeft = endOfDay.getTime() - now.getTime();
  return Math.max(1, Math.ceil(millisLeft / 3_600_000));
}
