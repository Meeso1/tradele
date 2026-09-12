import { useCallback, useEffect, useState } from "react";

const USER_ID_KEY = "tradele.userId";

interface Portfolio {
  cash: number;
  holdings: Record<string, number>;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; userId: string; portfolio: Portfolio };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

/**
 * Return the locally stored user ID, creating a new anonymous user via the
 * API on first visit and persisting the ID in localStorage.
 */
async function ensureUserId(): Promise<string> {
  const stored = localStorage.getItem(USER_ID_KEY);
  if (stored) {
    return stored;
  }
  const { id } = await request<{ id: string }>("/api/users", { method: "POST" });
  localStorage.setItem(USER_ID_KEY, id);
  return id;
}

async function loadSession(): Promise<{ userId: string; portfolio: Portfolio }> {
  const userId = await ensureUserId();
  const { access_token: token } = await request<{ access_token: string }>("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  const portfolio = await request<Portfolio>("/api/portfolio", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return { userId, portfolio };
}

export default function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(() => {
    setState({ status: "loading" });
    loadSession().then(
      ({ userId, portfolio }) => setState({ status: "ready", userId, portfolio }),
      (error: unknown) =>
        setState({
          status: "error",
          message: error instanceof Error ? error.message : String(error),
        }),
    );
  }, []);

  useEffect(load, [load]);

  const resetLocalUser = () => {
    localStorage.removeItem(USER_ID_KEY);
    load();
  };

  return (
    <main>
      <h1>Tradele</h1>
      <p className="tagline">A daily stock-trading guessing game.</p>

      {state.status === "loading" && <p>Loading…</p>}

      {state.status === "error" && (
        <section className="card error">
          <p>Something went wrong: {state.message}</p>
          <button onClick={resetLocalUser}>Reset local user and retry</button>
        </section>
      )}

      {state.status === "ready" && (
        <section className="card">
          <h2>Your portfolio</h2>
          <p>
            Cash: <strong>${state.portfolio.cash.toFixed(2)}</strong>
          </p>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Shares</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(state.portfolio.holdings).map(([symbol, quantity]) => (
                <tr key={symbol}>
                  <td>{symbol}</td>
                  <td>{quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="user-id">
            User ID: <code>{state.userId}</code> (stored in your browser)
          </p>
        </section>
      )}
    </main>
  );
}
