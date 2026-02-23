export function PortfolioPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-foreground">Portfolio Intelligence</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Track PE/PB ratios, volatility, and risk metrics for your watchlist.
      </p>
      <div className="mt-8 rounded-xl border border-border bg-accent/20 p-12 text-center">
        <p className="text-muted-foreground text-sm">
          Portfolio analytics will be available once the backend quantitative engine is connected.
        </p>
      </div>
    </div>
  );
}
