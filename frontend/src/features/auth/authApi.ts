import { BACKEND_URL, ApiError } from "../../shared/api/core";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  phone_number: string | null;
  expertise_level: string;
  profile_pic_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SendOtpResponse {
  message: string;
  expires_in_seconds: number;
}

export interface AuthResponse {
  message: string;
  user: AuthUser;
  is_new_user: boolean;
}

async function authFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const csrfToken = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] ?? "";

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (options.method && ["POST", "PUT", "PATCH", "DELETE"].includes(options.method)) {
    headers["X-CSRF-Token"] = decodeURIComponent(csrfToken);
    if (options.body && typeof options.body === "string") {
      headers["Content-Type"] = "application/json";
    }
  }

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(data.detail || "Request failed", response.status);
  }

  return data as T;
}

export async function sendOtp(
  email: string,
  purpose: "signup" | "login",
): Promise<SendOtpResponse> {
  return authFetch<SendOtpResponse>("/auth/send-otp", {
    method: "POST",
    body: JSON.stringify({ email, purpose }),
  });
}

export async function verifyOtp(
  email: string,
  otp: string,
  purpose: "signup" | "login",
  fullName?: string,
): Promise<AuthResponse> {
  return authFetch<AuthResponse>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ email, otp, purpose, full_name: fullName }),
  });
}

export async function refreshAuth(): Promise<void> {
  await authFetch<{ message: string }>("/auth/refresh", {
    method: "POST",
  });
}

export async function logoutAuth(): Promise<void> {
  await authFetch<{ message: string }>("/auth/logout", {
    method: "POST",
  });
}

export async function fetchMe(): Promise<AuthUser> {
  return authFetch<AuthUser>("/auth/me");
}

export async function updateProfile(
  data: { full_name?: string; phone_number?: string; expertise_level?: string },
): Promise<AuthUser> {
  return authFetch<AuthUser>("/auth/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
