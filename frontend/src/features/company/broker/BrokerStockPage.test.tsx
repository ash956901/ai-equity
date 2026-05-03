/// <reference types="vitest/globals" />
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";

vi.mock("../../../shared/api/quotes", () => ({
  fetchQuote: vi.fn(),
  fetchCandles: vi.fn(),
  fetchPeers: vi.fn(),
}));

import { fetchCandles, fetchQuote, fetchPeers } from "../../../shared/api/quotes";
import { BrokerStockPage } from "./BrokerStockPage";

const mockedFetchQuote = fetchQuote as unknown as ReturnType<typeof vi.fn>;
const mockedFetchCandles = fetchCandles as unknown as ReturnType<typeof vi.fn>;
const mockedFetchPeers = fetchPeers as unknown as ReturnType<typeof vi.fn>;

const SAMPLE_CANDLES = {
  ticker: "RELIANCE",
  exchange: "NSE",
  range: "1Y",
  interval: "1d",
  source: "yfinance",
  ohlcv: Array.from({ length: 5 }, (_, i) => ({
    t: `2024-0${i + 1}-01T00:00:00Z`,
    o: 100 + i,
    h: 110 + i,
    l: 95 + i,
    c: 105 + i,
    v: 1_000_000 + i,
  })),
};

beforeEach(() => {
  mockedFetchQuote.mockResolvedValue({
    ticker: "RELIANCE",
    name: "Reliance Industries",
    exchange: "NSE",
    company_id: "c-1",
    sector: "Energy",
    industry: "Oil & Gas Refining",
    last_price: 2845,
    change_pct: 1.4,
    open: 2810,
    prev_close: 2806,
    day_high: 2860,
    day_low: 2802,
    volume: 4_000_000,
  });
  mockedFetchCandles.mockResolvedValue(SAMPLE_CANDLES);
  mockedFetchPeers.mockResolvedValue([]);
});

describe("<BrokerStockPage>", () => {
  it("requests candles for the default range and shows quote header", async () => {
    renderWithProviders(<BrokerStockPage ticker="RELIANCE" />, { noAuth: true });

    // Quote header shows the resolved name.
    await waitFor(() => {
      expect(screen.getByText("Reliance Industries")).toBeInTheDocument();
    });

    // Fetch was called with default range.
    expect(mockedFetchCandles).toHaveBeenCalledWith("RELIANCE", "1Y");
  });

  it("re-fetches candles when the range toggle changes", async () => {
    renderWithProviders(<BrokerStockPage ticker="RELIANCE" />, { noAuth: true });
    await waitFor(() => {
      expect(mockedFetchCandles).toHaveBeenCalledWith("RELIANCE", "1Y");
    });

    fireEvent.click(screen.getByRole("tab", { name: "1M" }));
    await waitFor(() => {
      expect(mockedFetchCandles).toHaveBeenCalledWith("RELIANCE", "1M");
    });
  });

  it("switches between line and candle modes", async () => {
    renderWithProviders(<BrokerStockPage ticker="RELIANCE" />, { noAuth: true });
    await waitFor(() => screen.getByText("Reliance Industries"));

    const candleBtn = screen.getByRole("button", { name: "Candle" });
    expect(candleBtn).not.toHaveClass("is-active");
    fireEvent.click(candleBtn);
    expect(candleBtn).toHaveClass("is-active");

    const lineBtn = screen.getByRole("button", { name: "Line" });
    fireEvent.click(lineBtn);
    expect(lineBtn).toHaveClass("is-active");
  });

  it("shows an Ask-Minerva FAB when callback is provided", async () => {
    const onAsk = vi.fn();
    renderWithProviders(
      <BrokerStockPage ticker="RELIANCE" onAskMinerva={onAsk} />,
      { noAuth: true },
    );
    await waitFor(() => screen.getByText("Reliance Industries"));

    const fab = screen.getByRole("button", { name: /Ask Minerva/i });
    fireEvent.click(fab);
    expect(onAsk).toHaveBeenCalledTimes(1);
    const arg = onAsk.mock.calls[0][0] as string;
    expect(arg.toLowerCase()).toContain("reliance");
  });
});
