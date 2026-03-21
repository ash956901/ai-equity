import { FileText, Search, Filter } from "lucide-react";

export function FilingsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Filings</h1>
          <p className="text-sm text-muted-foreground">
            Browse the latest NSE/BSE filings, quarterly results, and investor presentations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search filings…"
              disabled
              className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none w-40 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <button
            disabled
            className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-sm text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Filter className="h-4 w-4" />
            Filter
          </button>
        </div>
      </div>

      <div className="flex flex-col items-center rounded-xl border border-dashed border-border bg-card/50 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-3">
          <FileText className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground max-w-sm">
          Filing data will appear here once the scraping pipeline is active.
        </p>
      </div>
    </div>
  );
}
