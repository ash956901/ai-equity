import { type ApiStatusResponse, type HealthResponse } from "../types/api";

export const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
  "http://localhost:8001";

/** @deprecated Use BACKEND_URL — all APIs now run on a single server. */
export const AI_BACKEND_URL = BACKEND_URL;

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ----------------------------------------------------------------------- //
// Auth token store + 401 refresh interceptor.                            //
// ----------------------------------------------------------------------- //

const ACCESS_TOKEN_KEY = "eq.access_token";
const REFRESH_TOKEN_KEY = "eq.refresh_token";

type AuthListener = (loggedIn: boolean) => void;
const authListeners = new Set<AuthListener>();

export function getAccessToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthTokens(access: string, refresh: string): void {
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  } catch {
    /* ignore */
  }
  authListeners.forEach((cb) => cb(true));
}

export function clearAuthTokens(): void {
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    /* ignore */
  }
  authListeners.forEach((cb) => cb(false));
}

export function subscribeAuth(cb: AuthListener): () => void {
  authListeners.add(cb);
  return () => authListeners.delete(cb);
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  const refresh = getRefreshToken();
  if (!refresh) return null;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        clearAuthTokens();
        return null;
      }
      const data = (await res.json()) as { access_token: string; refresh_token: string };
      setAuthTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      clearAuthTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

function buildHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(extra as Record<string, string>),
  };
  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function fetchWithAuth(
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: buildHeaders(init.headers),
    });
    if (response.status === 401 && getRefreshToken()) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        response = await fetch(`${BACKEND_URL}${path}`, {
          ...init,
          signal: controller.signal,
          headers: buildHeaders(init.headers),
        });
      }
    }
    return response;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// ----------------------------------------------------------------------- //
// Public fetch helpers (now auth-aware).                                  //
// ----------------------------------------------------------------------- //

export async function getJson<T>(path: string, timeoutMs = 12000): Promise<T> {
  try {
    const response = await fetchWithAuth(path, { method: "GET" }, timeoutMs);
    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not connect to backend");
  }
}

export async function aiGet<T>(path: string, timeoutMs = 30000): Promise<T> {
  try {
    const response = await fetchWithAuth(path, { method: "GET" }, timeoutMs);
    if (!response.ok) {
      throw new ApiError(`AI request failed with status ${response.status}`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("AI request timed out");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not connect to AI backend");
  }
}

export async function aiPost<T>(
  path: string,
  body: unknown,
  timeoutMs = 60000,
): Promise<T> {
  try {
    const response = await fetchWithAuth(
      path,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      timeoutMs,
    );
    if (!response.ok) {
      const detail = await safeReadDetail(response);
      throw new ApiError(detail || `AI request failed with status ${response.status}`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("AI request timed out");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not connect to AI backend");
  }
}

export async function aiPut<T>(
  path: string,
  body: unknown,
  timeoutMs = 30000,
): Promise<T> {
  const response = await fetchWithAuth(
    path,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    timeoutMs,
  );
  if (!response.ok) {
    const detail = await safeReadDetail(response);
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export async function aiDelete(path: string): Promise<void> {
  const response = await fetchWithAuth(path, { method: "DELETE" }, 30000);
  if (!response.ok) {
    throw new ApiError(`Delete failed with status ${response.status}`, response.status);
  }
}

/** Multipart file upload with auth header injection + 401 refresh. */
export async function aiUpload<T>(
  path: string,
  formData: FormData,
  timeoutMs = 120000,
): Promise<T> {
  const response = await fetchWithAuth(
    path,
    { method: "POST", body: formData },
    timeoutMs,
  );
  if (!response.ok) {
    const detail = await safeReadDetail(response);
    throw new ApiError(
      detail || `Upload failed with status ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

async function safeReadDetail(response: Response): Promise<string | null> {
  try {
    const json = (await response.json()) as { detail?: string };
    return typeof json.detail === "string" ? json.detail : null;
  } catch {
    return null;
  }
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function fetchApiStatus(): Promise<ApiStatusResponse> {
  return getJson<ApiStatusResponse>("/api/v1/status");
}
