import { useEffect, useState } from "react";
import { fetchInsightsFeed, type Insight } from "../lib/api";
import { Card, Chip, Skeleton } from "../components/ui";
import { Icon } from "../components/Icon";

interface Props {
  onOpenCompany: (id: string) => void;
}

const TYPES: { key: string; label: string }[] = [
  { key: "", label: "All" },
  { key: "red_flag", label: "Red flags" },
  { key: "risk", label: "Risks" },
  { key: "opportunity", label: "Opportunities" },
  { key: "guidance", label: "Guidance" },
  { key: "hidden_signal", label: "Hidden signals" },
  { key: "management_tone", label: "Mgmt tone" },
];

const SEVERITIES = ["", "high", "medium", "low"];

export function typeMeta(t: string): { icon: string; tone: "negative" | "warning" | "positive" | "neutral" | "tag"; label: string } {
  switch (t) {
    case "red_flag": return { icon: "flag", tone: "negative", label: "Red flag" };
    case "risk": return { icon: "warning", tone: "warning", label: "Risk" };
    case "opportunity": return { icon: "trending_up", tone: "positive", label: "Opportunity" };
    case "guidance": return { icon: "explore", tone: "neutral", label: "Guidance" };
    case "hidden_signal": return { icon: "visibility", tone: "tag", label: "Hidden signal" };
    case "management_tone": return { icon: "record_voice_over", tone: "neutral", label: "Mgmt tone" };
    default: return { icon: "lightbulb", tone: "neutral", label: t };
  }
}

const SEV_TONE: Record<string, string> = {
  high: "text-negative",
  medium: "text-warning",
  low: "text-on-surface-variant",
};

export function InsightsView({ onOpenCompany }: Props) {
  const [items, setItems] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState("");
  const [severity, setSeverity] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInsightsFeed({ insight_type: type || undefined, severity: severity || undefined, limit: 80 })
      .then((r) => !cancelled && setItems(r))
      .catch(() => !cancelled && setError("Could not load insights."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [type, severity]);

  return (
    <div className="space-y-lg">
      <div>
        <h1 className="text-headline-lg font-semibold text-on-surface">Document Insights</h1>
        <p className="text-body-sm text-on-surface-variant mt-1 max-w-2xl">
          Non-obvious signals extracted by Minerva from concall transcripts, annual reports,
          and filings — red flags, guidance shifts, and hidden exposures.
        </p>
      </div>

      {/* Filters */}
      <div className="space-y-sm">
        <div className="flex flex-wrap gap-sm">
          {TYPES.map((t) => (
            <button
              key={t.key}
              onClick={() => setType(t.key)}
              className={`h-9 px-md rounded-lg text-body-sm border transition-colors ${
                type === t.key
                  ? "bg-primary/15 border-primary/40 text-primary"
                  : "bg-bg-1 border-outline-variant text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-sm">
          <span className="text-label-caps font-label-caps text-on-surface-variant">Severity</span>
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`h-8 px-sm rounded-md text-caption capitalize border transition-colors ${
                severity === s
                  ? "bg-primary/15 border-primary/40 text-primary"
                  : "bg-bg-1 border-outline-variant text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {s || "all"}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="p-lg space-y-sm">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-full" />
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-lg text-body-sm text-negative">{error}</Card>
      ) : items.length === 0 ? (
        <Card className="p-2xl text-center text-body-sm text-on-surface-variant">
          No insights yet for this filter. The corpus builder enriches documents in the background.
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
          {items.map((it) => (
            <InsightCard key={it.id} it={it} onOpen={() => onOpenCompany(it.company_id)} />
          ))}
        </div>
      )}
    </div>
  );
}

export function InsightCard({ it, onOpen }: { it: Insight; onOpen: () => void }) {
  const meta = typeMeta(it.insight_type);
  return (
    <Card className="p-lg flex flex-col gap-sm">
      <div className="flex items-center justify-between gap-sm">
        <Chip tone={meta.tone}>
          <Icon name={meta.icon} className="text-[13px] mr-1" />
          {meta.label}
        </Chip>
        <span className={`text-label-caps font-label-caps ${SEV_TONE[it.severity] ?? "text-on-surface-variant"}`}>
          {it.severity}
        </span>
      </div>

      <div className="text-card-title font-semibold text-on-surface leading-snug">{it.title}</div>
      {it.detail && <p className="text-body-sm text-on-surface-variant">{it.detail}</p>}
      {it.source_quote && (
        <blockquote className="text-body-sm text-on-surface-variant border-l-2 border-outline pl-md italic">
          “{it.source_quote}”
        </blockquote>
      )}

      <div className="flex items-center justify-between pt-xs mt-auto border-t border-outline-variant/60">
        <button onClick={onOpen} className="text-body-sm text-primary font-medium hover:underline truncate">
          {it.ticker ?? it.company_name ?? "Company"}
        </button>
        <span className="text-caption text-on-surface-variant truncate max-w-[50%]">
          {it.doc_type ?? it.filing_title ?? ""}
          {it.period ? ` · ${it.period}` : ""}
        </span>
      </div>
    </Card>
  );
}
