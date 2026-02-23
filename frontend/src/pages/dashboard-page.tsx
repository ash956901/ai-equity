import { TrendingUp, FileText, Newspaper, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";

const quickActions = [
  {
    to: "/chat",
    icon: MessageSquare,
    title: "Iris Chat",
    description: "Ask Iris about equity research, filings, or market sentiment.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
  },
  {
    to: "/portfolio",
    icon: TrendingUp,
    title: "Portfolio",
    description: "Track PE/PB ratios, volatility, and risk metrics.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    to: "/filings",
    icon: FileText,
    title: "Filings",
    description: "Browse latest NSE/BSE filings and investor presentations.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    to: "/news",
    icon: Newspaper,
    title: "News & Sentiment",
    description: "Real-time sentiment analysis and thematic discovery.",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
  },
];

export function DashboardPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Welcome to your AI-powered equity research platform.
        </p>
      </div>

      {/* Stats row — placeholder for future data */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Watchlist", value: "—", sub: "No stocks tracked yet" },
          { label: "Filings Today", value: "—", sub: "Connect data pipeline" },
          { label: "Sentiment", value: "—", sub: "Awaiting news feed" },
          { label: "Iris Queries", value: "0", sub: "Start a conversation" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-border bg-accent/30 p-4"
          >
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className="mt-1 text-2xl font-semibold text-foreground">
              {stat.value}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-medium text-foreground mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {quickActions.map(({ to, icon: Icon, title, description, color, bg }) => (
            <Link
              key={to}
              to={to}
              className="group flex items-start gap-4 rounded-xl border border-border bg-accent/20 p-5 transition-colors hover:bg-accent/40"
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${bg}`}
              >
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                  {title}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  {description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Timeline placeholder */}
      <div className="rounded-xl border border-border bg-accent/20 p-6">
        <h2 className="text-lg font-medium text-foreground mb-2">
          Automated Timeline
        </h2>
        <p className="text-sm text-muted-foreground">
          Actionable insights from daily filings will appear here once the data
          pipeline is connected.
        </p>
      </div>
    </div>
  );
}
