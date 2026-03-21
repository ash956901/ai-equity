import { TrendingUp, FileText, Newspaper, MessageSquare, ArrowRight, Sparkles, BarChart3, Globe, Clock } from "lucide-react";
import { Link } from "react-router-dom";

const stats = [
  { label: "Watchlist", value: "—", sub: "No stocks tracked yet", icon: BarChart3, color: "text-indigo-400" },
  { label: "Filings Today", value: "—", sub: "Connect data pipeline", icon: FileText, color: "text-amber-400" },
  { label: "Market Sentiment", value: "—", sub: "Awaiting news feed", icon: Globe, color: "text-emerald-400" },
  { label: "Iris Queries", value: "0", sub: "Start a conversation", icon: Sparkles, color: "text-primary" },
];

const quickActions = [
  {
    to: "/chat",
    icon: MessageSquare,
    title: "Iris Chat",
    description: "Ask Iris about equity research, filings, or market sentiment.",
    gradient: "from-indigo-500/10 to-purple-500/10",
    iconColor: "text-indigo-400",
  },
  {
    to: "/portfolio",
    icon: TrendingUp,
    title: "Portfolio",
    description: "Track PE/PB ratios, volatility, and risk metrics.",
    gradient: "from-emerald-500/10 to-teal-500/10",
    iconColor: "text-emerald-400",
  },
  {
    to: "/filings",
    icon: FileText,
    title: "Filings",
    description: "Browse latest NSE/BSE filings and investor presentations.",
    gradient: "from-amber-500/10 to-orange-500/10",
    iconColor: "text-amber-400",
  },
  {
    to: "/news",
    icon: Newspaper,
    title: "News & Sentiment",
    description: "Real-time sentiment analysis and thematic discovery.",
    gradient: "from-rose-500/10 to-pink-500/10",
    iconColor: "text-rose-400",
  },
];

export function DashboardPage() {
  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Welcome to your AI-powered equity research platform.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, sub, icon: Icon, color }) => (
          <div
            key={label}
            className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-colors hover:border-border/80"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
                <p className="mt-2 text-3xl font-bold text-foreground">{value}</p>
              </div>
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg bg-muted/50 ${color}`}>
                <Icon className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{sub}</p>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-foreground">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {quickActions.map(({ to, icon: Icon, title, description, gradient, iconColor }) => (
            <Link
              key={to}
              to={to}
              className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5"
            >
              <div className={`absolute inset-0 bg-linear-to-br ${gradient} opacity-0 transition-opacity group-hover:opacity-100`} />
              <div className="relative flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted/50">
                  <Icon className={`h-5 w-5 ${iconColor}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">
                      {title}
                    </h3>
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    {description}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-foreground">
            Automated Timeline
          </h2>
        </div>
        <div className="flex flex-col items-center py-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-3">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            Actionable insights from daily filings will appear here once the data
            pipeline is connected.
          </p>
        </div>
      </div>
    </div>
  );
}
