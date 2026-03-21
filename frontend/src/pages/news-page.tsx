import { Newspaper, TrendingUp, TrendingDown, Minus } from "lucide-react";

const gauges = [
  { label: "Bullish", value: "—", icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  { label: "Neutral", value: "—", icon: Minus, color: "text-amber-400", bg: "bg-amber-500/10" },
  { label: "Bearish", value: "—", icon: TrendingDown, color: "text-rose-400", bg: "bg-rose-500/10" },
];

export function NewsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">News &amp; Sentiment</h1>
        <p className="text-sm text-muted-foreground">
          Real-time news sentiment analysis and N-th order thematic discovery.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {gauges.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${bg}`}>
                <Icon className={`h-4 w-4 ${color}`} />
              </div>
            </div>
            <p className="mt-2 text-3xl font-bold text-foreground">{value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center rounded-xl border border-dashed border-border bg-card/50 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-3">
          <Newspaper className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground max-w-sm">
          Sentiment tracking will activate once the FinBERT pipeline and news scrapers are connected.
        </p>
      </div>
    </div>
  );
}
