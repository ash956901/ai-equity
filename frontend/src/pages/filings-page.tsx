export function FilingsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-foreground">Filings</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Browse the latest NSE/BSE filings, quarterly results, and investor presentations.
      </p>
      <div className="mt-8 rounded-xl border border-border bg-accent/20 p-12 text-center">
        <p className="text-muted-foreground text-sm">
          Filing data will appear here once the scraping pipeline is active.
        </p>
      </div>
    </div>
  );
}
