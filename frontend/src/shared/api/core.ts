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

const NGROK_SKIP_HEADER = { "ngrok-skip-browser-warning": "true" };

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function isMutating(method: string): boolean {
  return ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase());
}

function buildHeaders(
  extra: Record<string, string> = {},
  method?: string,
): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...NGROK_SKIP_HEADER,
    ...extra,
  };

  if (method && isMutating(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers["X-CSRF-Token"] = csrf;
    }
  }

  return headers;
}

export async function getJson<T>(path: string, timeoutMs = 12000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      signal: controller.signal,
      credentials: "include",
      headers: buildHeaders({}, "GET"),
    });

    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out");
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError("Could not connect to backend");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function aiGet<T>(path: string, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${AI_BACKEND_URL}${path}`, {
      signal: controller.signal,
      credentials: "include",
      headers: buildHeaders({}, "GET"),
    });

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
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function aiPost<T>(path: string, body: unknown, timeoutMs = 120000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${AI_BACKEND_URL}${path}`, {
      method: "POST",
      signal: controller.signal,
      credentials: "include",
      headers: buildHeaders({ "Content-Type": "application/json" }, "POST"),
      body: JSON.stringify(body),
    });

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
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function aiPut<T>(path: string, body: unknown, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${AI_BACKEND_URL}${path}`, {
      method: "PUT",
      signal: controller.signal,
      credentials: "include",
      headers: buildHeaders({ "Content-Type": "application/json" }, "PUT"),
      body: JSON.stringify(body),
    });

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
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function aiDelete(path: string): Promise<void> {
  const response = await fetch(`${AI_BACKEND_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
    headers: buildHeaders({}, "DELETE"),
  });
  if (!response.ok) {
    throw new ApiError(`Delete failed with status ${response.status}`, response.status);
  }
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function fetchApiStatus(): Promise<ApiStatusResponse> {
  return getJson<ApiStatusResponse>("/api/v1/status");
}
