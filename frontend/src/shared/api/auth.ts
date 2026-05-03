/**
 * Auth API client for the FastAPI auth domain.
 * Backed by `/auth/*` endpoints and ../core token store.
 */
import { aiPost, clearAuthTokens, getJson, setAuthTokens } from "./core";

export interface CurrentUser {
  id: string;
  email: string;
  username?: string | null;
  full_name?: string | null;
  expertise_level: string;
  risk_tolerance?: string | null;
  investment_horizon?: string | null;
  avatar_url?: string | null;
  theme_preference?: string | null;
  default_chart_range?: string | null;
  sectors_of_interest?: string[] | null;
  email_verified_at?: string | null;
  last_login_at?: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface SignupResponse {
  user: CurrentUser;
  tokens: TokenPair;
  email_verification_required: boolean;
}

export async function signup(args: {
  email: string;
  username?: string;
  password: string;
  full_name?: string;
}): Promise<SignupResponse> {
  const data = await aiPost<SignupResponse>("/auth/signup", args, 20000);
  if (data.tokens?.access_token && data.tokens?.refresh_token) {
    setAuthTokens(data.tokens.access_token, data.tokens.refresh_token);
  }
  return data;
}

export async function login(args: {
  identifier: string;
  password: string;
}): Promise<TokenPair> {
  const data = await aiPost<TokenPair>("/auth/login", args, 15000);
  setAuthTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await aiPost<void>("/auth/logout", {});
  } catch {
    /* even if backend rejects, clear locally */
  }
  clearAuthTokens();
}

export async function fetchMe(): Promise<CurrentUser> {
  return getJson<CurrentUser>("/auth/me");
}

export async function forgotPassword(email: string): Promise<void> {
  await aiPost<void>("/auth/forgot-password", { email });
}

export async function resetPassword(args: {
  token: string;
  new_password: string;
}): Promise<void> {
  await aiPost<void>("/auth/reset-password", args);
}

export async function verifyEmail(token: string): Promise<CurrentUser> {
  return aiPost<CurrentUser>("/auth/verify-email", { token });
}
