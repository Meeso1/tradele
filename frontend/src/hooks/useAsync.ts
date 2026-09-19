import { useCallback, useEffect, useState } from "react";

export interface AsyncResource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

interface UseAsyncOptions {
  /** Keep the previous result visible while the new deps load (default true). */
  readonly keepPreviousData?: boolean;
}

/**
 * Minimal async data loader: runs `load` on mount and whenever `deps`
 * change, exposing data/loading/error plus a manual `reload`. Cancels
 * stale results when the deps change mid-flight. By default the previous
 * result stays in `data` until the new one arrives; pass
 * `{ keepPreviousData: false }` to clear it instead (for callers that
 * render their own previous-data placeholder).
 */
export function useAsync<T>(
  load: () => Promise<T>,
  deps: readonly unknown[],
  options: UseAsyncOptions = {},
): AsyncResource<T> {
  const keepPreviousData = options.keepPreviousData ?? true;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    if (!keepPreviousData) setData(null);
    load()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : "Something went wrong");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Callers pass the dependency list explicitly, mirroring useEffect.
  }, [...deps, attempt]);

  const reload = useCallback(() => setAttempt((previous) => previous + 1), []);

  return { data, loading, error, reload };
}
