/**
 * Low-level API client: a fetch wrapper with bearer-token auth, plus the
 * anonymous session bootstrap (create a user, mint an access token).
 *
 * All API URLs are relative ("/api/...") so calls are same-origin in both
 * dev (Vite proxy) and production (FastAPI serves the built frontend).
 */

import type { CreateUserResponseDto, IssueTokenResponseDto } from "./dto";

const API_BASE = "/api";
const TOKEN_STORAGE_KEY = "tradele:access-token";
const USER_ID_STORAGE_KEY = "tradele:user-id";

/** Error thrown for any non-2xx API response; `status` is the HTTP status. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let accessToken: string | null = localStorage.getItem(TOKEN_STORAGE_KEY);

function storeAccessToken(token: string): void {
  accessToken = token;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearAccessToken(): void {
  accessToken = null;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  retried = false,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (accessToken != null) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && !retried) {
    // Stale/invalid token: re-bootstrap the session once, then retry.
    clearAccessToken();
    await ensureSession();
    return request<T>(method, path, body, true);
  }
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const payload: unknown = await response.json();
    if (typeof payload === "object" && payload != null && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "string") message = detail;
    }
  } catch {
    // Non-JSON body - keep the generic message.
  }
  return new ApiError(response.status, message);
}

/**
 * Ensure a usable session: reuse the stored access token, or (creating the
 * anonymous user first, if needed) mint a fresh one. Safe to call repeatedly;
 * every protected endpoint requires a token, so the app runs this at startup.
 */
export async function ensureSession(): Promise<void> {
  if (accessToken != null) return;

  const storedUserId = localStorage.getItem(USER_ID_STORAGE_KEY);
  if (storedUserId != null) {
    try {
      await mintToken(storedUserId);
      return;
    } catch (error) {
      // The stored user no longer exists server-side - create a new one.
      if (!(error instanceof ApiError) || error.status !== 404) throw error;
      localStorage.removeItem(USER_ID_STORAGE_KEY);
    }
  }

  const created = await apiPost<CreateUserResponseDto>("/users", {});
  localStorage.setItem(USER_ID_STORAGE_KEY, created.id);
  await mintToken(created.id);
}

async function mintToken(userId: string): Promise<void> {
  const issued = await apiPost<IssueTokenResponseDto>("/auth/token", { user_id: userId });
  storeAccessToken(issued.access_token);
}
