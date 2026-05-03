/// <reference types="vitest/globals" />
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { login, logout, signup } from "./auth";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
} from "./core";

const ORIGINAL_FETCH = globalThis.fetch;

function mockJsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("shared/api/auth", () => {
  beforeEach(() => {
    clearAuthTokens();
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = ORIGINAL_FETCH;
    clearAuthTokens();
  });

  it("signup persists tokens to localStorage", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockJsonResponse({
        user: {
          id: "00000000-0000-0000-0000-000000000001",
          email: "test@equityai.local",
          username: null,
          full_name: null,
          expertise_level: "beginner",
          created_at: "2026-04-30T00:00:00",
        },
        tokens: {
          access_token: "ACCESS",
          refresh_token: "REFRESH",
          token_type: "bearer",
          expires_in: 900,
        },
        email_verification_required: false,
      }),
    );

    const result = await signup({
      email: "test@equityai.local",
      password: "password1234",
    });

    expect(result.user.email).toBe("test@equityai.local");
    expect(result.tokens.access_token).toBe("ACCESS");
    expect(getAccessToken()).toBe("ACCESS");
    expect(getRefreshToken()).toBe("REFRESH");
  });

  it("login persists tokens to localStorage", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockJsonResponse({
        access_token: "AAA",
        refresh_token: "RRR",
        token_type: "bearer",
        expires_in: 900,
      }),
    );

    await login({ identifier: "test@equityai.local", password: "password1234" });

    expect(getAccessToken()).toBe("AAA");
    expect(getRefreshToken()).toBe("RRR");
  });

  it("logout clears tokens even when the server call rejects", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("network down"),
    );
    // Pretend we were logged in.
    window.localStorage.setItem("eq.access_token", "ACCESS");
    window.localStorage.setItem("eq.refresh_token", "REFRESH");

    await logout();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});
