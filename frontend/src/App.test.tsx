import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App shell", () => {
  it("renders key shell controls", () => {
    render(<App />);

    expect(screen.getByText("EquityAI")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open notifications" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Command Palette/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Global Search/i })).toBeInTheDocument();
  });

  it("opens command palette with keyboard shortcut", () => {
    render(<App />);

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });

    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search commands, pages, and actions...")).toBeInTheDocument();
  });

  it("opens global search with keyboard shortcut", () => {
    render(<App />);

    fireEvent.keyDown(window, { key: "j", ctrlKey: true });

    expect(screen.getByRole("dialog", { name: "Global search" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Try: RELIANCE, defense, AI, risk...")).toBeInTheDocument();
  });

  it("navigates to settings view from sidebar", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Settings/i }));

    expect(screen.getByText("Workspace Settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Switch to Demo Data/i })).toBeInTheDocument();
  });

  it("toggles theme mode from settings", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Settings/i }));
    expect(screen.getByRole("button", { name: /Use Dark Mode/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Use Dark Mode/i }));

    expect(screen.getByRole("button", { name: /Use Light Mode/i })).toBeInTheDocument();
  });
});
