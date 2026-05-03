/// <reference types="vitest/globals" />
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "./test/renderWithProviders";

// HomeView is the default landing view in Round 2 — stub its data layer so
// shell-level tests don't depend on a live backend.
vi.mock("./shared/api/home", () => ({
  fetchHomePersonalized: vi.fn().mockResolvedValue({
    user: { id: "u-test", username: null, expertise_level: "intermediate" },
    watchlist_companies: [],
    holdings_companies: [],
    asymmetric_feed: [],
    timeline_recent: [],
    suggestions: [],
    generated_at: "2026-04-30T00:00:00",
  }),
}));

vi.mock("./lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./lib/api")>();
  return { ...actual, searchCompaniesDB: vi.fn().mockResolvedValue([]) };
});

import App from "./App";

describe("App shell", () => {
  it("renders the EquityAI brand and notifications control", () => {
    renderWithProviders(<App />, { noAuth: true });

    expect(screen.getByText("EquityAI")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open notifications" }),
    ).toBeInTheDocument();
  });

  it("navigates to settings view from sidebar", () => {
    renderWithProviders(<App />, { noAuth: true });
    fireEvent.click(screen.getByRole("button", { name: /Settings/i }));
    // PageHeader for SettingsView passes title="Workspace Settings".
    expect(screen.getByText(/Workspace Settings/i)).toBeInTheDocument();
  });
});
