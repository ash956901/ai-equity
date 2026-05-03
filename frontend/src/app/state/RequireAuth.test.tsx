/// <reference types="vitest/globals" />
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { RequireAuth } from "./RequireAuth";

vi.mock("./AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "./AuthContext";

const mockedUseAuth = useAuth as unknown as ReturnType<typeof vi.fn>;

function setAuthState(state: {
  user: unknown;
  loading: boolean;
  initialised: boolean;
}) {
  mockedUseAuth.mockReturnValue({
    ...state,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
  });
}

function Children({ children }: { children: ReactNode }) {
  return <div data-testid="protected">{children}</div>;
}

describe("<RequireAuth>", () => {
  it("renders the loader while auth is initialising", () => {
    setAuthState({ user: null, loading: true, initialised: false });
    render(
      <RequireAuth fallback={<span data-testid="fallback">login</span>}>
        <Children>protected content</Children>
      </RequireAuth>,
    );
    expect(screen.queryByTestId("protected")).toBeNull();
    expect(screen.queryByTestId("fallback")).toBeNull();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders the fallback when no user is logged in", () => {
    setAuthState({ user: null, loading: false, initialised: true });
    render(
      <RequireAuth fallback={<span data-testid="fallback">login</span>}>
        <Children>protected content</Children>
      </RequireAuth>,
    );
    expect(screen.getByTestId("fallback")).toBeInTheDocument();
    expect(screen.queryByTestId("protected")).toBeNull();
  });

  it("renders children when a user is present", () => {
    setAuthState({
      user: { id: "u-1", email: "x@y.z", expertise_level: "intermediate" },
      loading: false,
      initialised: true,
    });
    render(
      <RequireAuth fallback={<span data-testid="fallback">login</span>}>
        <Children>protected content</Children>
      </RequireAuth>,
    );
    expect(screen.getByTestId("protected")).toBeInTheDocument();
    expect(screen.queryByTestId("fallback")).toBeNull();
  });
});
