import { useCallback, useEffect, useState } from "react";

export interface AsyncResource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Minimal async data loader: runs `load` on mount and whenever `deps`
 * change, exposing data/loading/error plus a manual `reload`. Cancels
 * stale results when the deps change mid-flight.
 */
export function useAsync<T>(load: () => Promise<T>, deps: readonly unknown[]): AsyncResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
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
