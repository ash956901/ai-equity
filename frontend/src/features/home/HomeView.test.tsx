/// <reference types="vitest/globals" />
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";

vi.mock("../../shared/api/home", () => ({
  fetchHomePersonalized: vi.fn(),
}));

import { fetchHomePersonalized } from "../../shared/api/home";
import { HomeView } from "./HomeView";

const mockedFetchHome = fetchHomePersonalized as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockedFetchHome.mockResolvedValue({
    user: { id: "u", username: null, expertise_level: "intermediate" },
    watchlist_companies: [
      {
        company_id: "c1",
        name: "Reliance Industries",
        ticker_nse: "RELIANCE",
        ticker_bse: "500325",
        sector: "Energy",
        industry: "Oil & Gas Refining",
      },
    ],
    holdings_companies: [
      {
        company_id: "c2",
        name: "Tata Consultancy Services",
        ticker_nse: "TCS",
        ticker_bse: "532540",
        sector: "Information Technology",
        industry: "IT Services",
        quantity: 10,
      },
    ],
    asymmetric_feed: [
      {
        company_id: "c3",
        name: "Castrol India",
        ticker_nse: "CASTROLIND",
        ticker_bse: null,
        sector: "Energy",
        industry: "Lubricants",
        theme: "data_centre_lubricants",
        impact_score: 0.7,
        exposure_type: "second_order",
        reasoning: "Specialty coolants used in DC immersion cooling.",
      },
    ],
    timeline_recent: [
      {
        filing_id: "f1",
        company_id: "c1",
        company_name: "Reliance Industries",
        ticker_nse: "RELIANCE",
        filing_type: "Quarterly_Results",
        filing_date: "2026-04-30",
        summary: "Q4 PAT up 12% YoY on retail margin expansion.",
      },
    ],
    suggestions: [],
    generated_at: "2026-04-30T00:00:00",
  });
});

describe("<HomeView>", () => {
  it("shows the loading state, then renders all rails", async () => {
    const onPick = vi.fn();
    renderWithProviders(<HomeView onPickCompany={onPick} />, { noAuth: true });

    expect(screen.getByText(/Loading your dashboard/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Your watchlist")).toBeInTheDocument();
    });
    expect(screen.getByText("Your holdings")).toBeInTheDocument();
    expect(screen.getByText(/Hidden \/ asymmetric exposure/i)).toBeInTheDocument();
    expect(screen.getByText("Recent filings (timeline)")).toBeInTheDocument();
    expect(screen.getByText("Suggested for you")).toBeInTheDocument();

    // Watchlist + holdings + asymmetric show their key companies.
    expect(screen.getByText("Reliance Industries")).toBeInTheDocument();
    expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
    expect(screen.getByText("Castrol India")).toBeInTheDocument();

    // Asymmetric badge shows the theme code.
    expect(screen.getByText("data_centre_lubricants")).toBeInTheDocument();
  });

  it("invokes onPickCompany with ticker + company_id when a card is clicked", async () => {
    const onPick = vi.fn();
    renderWithProviders(<HomeView onPickCompany={onPick} />, { noAuth: true });

    await waitFor(() => screen.getByText("Reliance Industries"));
    fireEvent.click(screen.getByText("Reliance Industries"));

    expect(onPick).toHaveBeenCalledWith("RELIANCE", "c1");
  });

  it("renders the empty-state copy when a rail has no entries", async () => {
    mockedFetchHome.mockResolvedValueOnce({
      user: { id: "u", username: null, expertise_level: "intermediate" },
      watchlist_companies: [],
      holdings_companies: [],
      asymmetric_feed: [],
      timeline_recent: [],
      suggestions: [],
      generated_at: "2026-04-30T00:00:00",
    });
    renderWithProviders(<HomeView onPickCompany={() => {}} />, { noAuth: true });
    await waitFor(() => screen.getByText("Your watchlist"));
    expect(
      screen.getByText("Add companies to start tracking them."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Connect a broker or add holdings manually."),
    ).toBeInTheDocument();
  });
});
