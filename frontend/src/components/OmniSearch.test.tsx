/// <reference types="vitest/globals" />
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../shared/api/home", () => ({
  fetchHomePersonalized: vi.fn(),
}));
vi.mock("../lib/api", () => ({
  searchCompaniesDB: vi.fn(),
}));

import { fetchHomePersonalized } from "../shared/api/home";
import { searchCompaniesDB } from "../lib/api";
import { OmniSearch } from "./OmniSearch";

const mockedFetchHome = fetchHomePersonalized as unknown as ReturnType<typeof vi.fn>;
const mockedSearch = searchCompaniesDB as unknown as ReturnType<typeof vi.fn>;

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
      },
    ],
    asymmetric_feed: [],
    timeline_recent: [],
    suggestions: [],
    generated_at: "2026-04-30T00:00:00",
  });
  mockedSearch.mockResolvedValue([]);
});

describe("<OmniSearch>", () => {
  it("shows the user's tracked companies as default suggestions on focus", async () => {
    const onPick = vi.fn();
    render(<OmniSearch onPick={onPick} />);

    // Default-results panel only opens after focus.
    fireEvent.focus(screen.getByPlaceholderText(/Search companies/i));

    await waitFor(() => {
      expect(screen.getByText("Your tracked companies")).toBeInTheDocument();
    });
    expect(screen.getByText("Reliance Industries")).toBeInTheDocument();
    expect(screen.getByText("Tata Consultancy Services")).toBeInTheDocument();
  });

  it("calls onPick with ticker + company_id when a default result is chosen", async () => {
    const onPick = vi.fn();
    render(<OmniSearch onPick={onPick} />);
    fireEvent.focus(screen.getByPlaceholderText(/Search companies/i));

    await waitFor(() => screen.getByText("Reliance Industries"));
    fireEvent.click(screen.getByText("Reliance Industries"));
    expect(onPick).toHaveBeenCalledWith("RELIANCE", "c1");
  });

  it("debounces query input before hitting the search endpoint", async () => {
    const onPick = vi.fn();
    mockedSearch.mockResolvedValue([
      { id: "c3", name: "Infosys", ticker_nse: "INFY", sector: "IT Services", symbol: "INFY" },
    ]);
    render(<OmniSearch onPick={onPick} />);
    const input = screen.getByPlaceholderText(/Search companies/i);
    fireEvent.focus(input);

    // Three keystrokes in quick succession should not fire 3 backend calls
    // because of the 200ms debounce.
    fireEvent.change(input, { target: { value: "I" } });
    fireEvent.change(input, { target: { value: "In" } });
    fireEvent.change(input, { target: { value: "Inf" } });
    expect(mockedSearch).not.toHaveBeenCalled();

    await waitFor(
      () => expect(mockedSearch).toHaveBeenCalledTimes(1),
      { timeout: 600 },
    );
    expect(mockedSearch).toHaveBeenCalledWith("Inf", 10);
  });
});
