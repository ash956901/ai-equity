export function NewsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-foreground">News & Sentiment</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Real-time news sentiment analysis and N-th order thematic discovery.
      </p>
      <div className="mt-8 rounded-xl border border-border bg-accent/20 p-12 text-center">
        <p className="text-muted-foreground text-sm">
          Sentiment tracking will activate once the FinBERT pipeline and news scrapers are connected.
        </p>
      </div>
    </div>
  );
}
