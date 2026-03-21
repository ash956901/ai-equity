import { TrendingUp, BarChart3, PieChart } from "lucide-react";

const features = [
  { icon: BarChart3, title: "Risk Metrics", description: "PE/PB ratios, beta, and volatility analysis.", color: "text-indigo-400" },
  { icon: TrendingUp, title: "Performance", description: "Historical returns and benchmark comparison.", color: "text-emerald-400" },
  { icon: PieChart, title: "Allocation", description: "Sector and market-cap distribution breakdown.", color: "text-amber-400" },
];

export function PortfolioPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Portfolio Intelligence</h1>
        <p className="text-sm text-muted-foreground">
          Track PE/PB ratios, volatility, and risk metrics for your watchlist.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {features.map(({ icon: Icon, title, description, color }) => (
          <div key={title} className="rounded-xl border border-border bg-card p-5">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg bg-muted/50 ${color} mb-3`}>
              <Icon className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center rounded-xl border border-dashed border-border bg-card/50 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-3">
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground max-w-sm">
          Portfolio analytics will be available once the backend quantitative engine is connected.
        </p>
      </div>
    </div>
  );
}
