import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  BarChart3,
  Bookmark,
  BookmarkCheck,
  Bot,
  Clock3,
  FileText,
  Loader2,
  Search,
  TrendingUp,
} from "lucide-react";
import type { jsPDF as JsPdfType } from "jspdf";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  fetchSecFilings,
  fetchCompanyDetail,
  fetchCompanyRatios,
  fetchCompanyQuote,
  searchCompaniesDB,
  fetchTimeline,
  enrichCompany,
  type SecFiling,
  type AICompany,
  type AIRatios,
  type AIQuote,
  type TimelineEvent as BackendTimelineEvent,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { SourceBadges } from "../../shared/ui/SourceBadges";

type DataMode = "live" | "demo";
type ToastTone = "info" | "success" | "warning";
type ViewKey = "filings" | "chat";

interface SearchSelection {
  stamp: number;
  companySymbol?: string;
  companyId?: string;
  filingsSymbol?: string;
  newsSymbol?: string;
  discoveryQuery?: string;
  chatPrompt?: string;
  reportScope?: "company" | "comparison";
  reportCompareSymbols?: string[];
}

type FavoriteType = "company" | "filing" | "headline";

interface FavoriteItem {
  id: string;
  type: FavoriteType;
  symbol?: string;
  title: string;
  subtitle?: string;
  url?: string;
  createdAt: string;
}

interface DiscoveryCompany {
  symbol: string;
  name: string;
  sector: string;
  marketCapBn: number;
  insight: string;
  themeScores: Record<string, number>;
}

interface TimelineEvent {
  id: string;
  company: string;
  title: string;
  summary: string;
  type: "filing" | "news" | "signal";
  impact: "high" | "medium" | "low";
  timestamp: string;
  sourceLabel: string;
  sourceUrl?: string;
  details: string[];
}

type ReportSectionId = "summary" | "risks" | "financials" | "themes";
type ReportAudience = "retail" | "analyst";

interface ReportSectionOption {
  id: ReportSectionId;
  label: string;
}

interface GeneratedReportSection {
  id: ReportSectionId;
  heading: string;
  content: string;
}

interface GeneratedReport {
  title: string;
  generatedAt: string;
  audience: ReportAudience;
  audienceText: string;
  symbol: string;
  companyName: string;
  dataMode: DataMode;
  scope: "company" | "comparison";
  compareSymbols?: string[];
  sections: GeneratedReportSection[];
  body: string;
}

interface PdfTemplate {
  coverLabel: string;
  accent: [number, number, number];
}

const PDF_TEMPLATES: Record<ReportAudience, PdfTemplate> = {
  retail: {
    coverLabel: "Retail Brief",
    accent: [15, 134, 186],
  },
  analyst: {
    coverLabel: "Analyst Dossier",
    accent: [17, 87, 131],
  },
};

const REPORT_SECTION_OPTIONS: ReportSectionOption[] = [
  { id: "summary", label: "Executive Summary" },
  { id: "risks", label: "Key Risks" },
  { id: "financials", label: "Financial Snapshot" },
  { id: "themes", label: "Theme Outlook" },
];

function normalizeSymbolsInput(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 4)
    )
  );
}

function toFileSlug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function wrapPdfText(doc: JsPdfType, text: string, maxWidth: number): string[] {
  return doc.splitTextToSize(text, maxWidth) as string[];
}

function renderPdfParagraph(
  doc: JsPdfType,
  text: string,
  leftX: number,
  rightX: number,
  startY: number
): number {
  const lines = wrapPdfText(doc, text, rightX - leftX);
  doc.text(lines, leftX, startY);
  return startY + lines.length * 6 + 2;
}

async function exportReportAsPdf(report: GeneratedReport): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginLeft = 16;
  const marginRight = pageWidth - 16;
  const template = PDF_TEMPLATES[report.audience];

  doc.setFillColor(template.accent[0], template.accent[1], template.accent[2]);
  doc.rect(0, 0, pageWidth, 46, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(24);
  doc.text("EquityAI Research Report", marginLeft, 20);
  doc.setFontSize(12);
  doc.setFont("helvetica", "normal");
  doc.text(template.coverLabel, marginLeft, 28);
  doc.text(`${report.companyName} (${report.symbol})`, marginLeft, 35);

  doc.setTextColor(18, 32, 45);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(report.title, marginLeft, 58);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const metadataLines = [
    `Generated: ${new Date(report.generatedAt).toLocaleString()}`,
    `Audience: ${report.audience === "retail" ? "Retail" : "Analyst"}`,
    `Data Mode: ${report.dataMode === "demo" ? "Demo Data" : "Live API"}`,
  ];

  let y = 66;
  for (const line of metadataLines) {
    doc.text(line, marginLeft, y);
    y += 5.5;
  }

  doc.setDrawColor(210, 220, 230);
  doc.line(marginLeft, y + 2, marginRight, y + 2);
  y += 10;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Executive Framing", marginLeft, y);
  y += 7;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  y = renderPdfParagraph(doc, report.audienceText, marginLeft, marginRight, y);

  for (const section of report.sections) {
    if (y > pageHeight - 30) {
      doc.addPage();
      y = 20;
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(section.heading, marginLeft, y);
    y += 7;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);

    const lines = section.content.split("\n");
    for (const line of lines) {
      if (!line.trim()) {
        y += 2;
        continue;
      }

      if (y > pageHeight - 16) {
        doc.addPage();
        y = 20;
      }

      y = renderPdfParagraph(doc, line, marginLeft, marginRight, y);
    }
    y += 4;
  }

  const pageCount = doc.getNumberOfPages();
  const scopeLabel = report.scope === "comparison" ? "Comparison" : "Company";
  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page);
    doc.setFontSize(9);
    doc.setTextColor(110, 122, 134);
    doc.text(
      `${scopeLabel} · ${report.symbol} · ${report.dataMode === "demo" ? "Demo" : "Live"} · Page ${page}/${pageCount}`,
      marginLeft,
      pageHeight - 8
    );
  }

  const filename =
    report.scope === "comparison"
      ? `${toFileSlug(report.symbol)}-comparison-report.pdf`
      : `${toFileSlug(report.symbol)}-${report.audience}-report.pdf`;
  doc.save(filename);
}

interface CompanyWorkspaceViewProps {
  dataMode: DataMode;
  pushToast: (message: string, tone?: ToastTone) => void;
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}

export function CompanyWorkspaceView(props: CompanyWorkspaceViewProps) {
  const { searchSelection, pushToast, dataMode } = props;

  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(
    () => searchSelection?.stamp ?? 0
  );
  const [symbolInput, setSymbolInput] = useState(() => {
    const s =
      searchSelection?.companySymbol ??
      searchSelection?.filingsSymbol ??
      searchSelection?.newsSymbol ??
      searchSelection?.discoveryQuery;
    return s ? s.toUpperCase() : "RELIANCE";
  });
  const [activeSymbol, setActiveSymbol] = useState(() => {
    const s =
      searchSelection?.companySymbol ??
      searchSelection?.filingsSymbol ??
      searchSelection?.newsSymbol ??
      searchSelection?.discoveryQuery;
    return s ? s.toUpperCase() : "RELIANCE";
  });
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(
    () => searchSelection?.companyId ?? null
  );
  const [activeTab, setActiveTab] = useState<"overview" | "filings" | "sentiment" | "timeline" | "chat">(
    "overview"
  );
  const [reportTitle, setReportTitle] = useState("");
  const [reportSections, setReportSections] = useState<ReportSectionId[]>([
    "summary",
    "risks",
    "financials",
    "themes",
  ]);
  const [reportAudience, setReportAudience] = useState<ReportAudience>("analyst");
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);
  const [reportScope, setReportScope] = useState<"company" | "comparison">("company");
  const [comparisonSymbols, setComparisonSymbols] = useState<string[]>([]);
  const [comparisonSymbolsInput, setComparisonSymbolsInput] = useState("");

  useEffect(() => {
    if (!searchSelection) return;
    if (searchSelection.stamp === lastSelectionStamp) return;

    const symbol =
      searchSelection.companySymbol ??
      searchSelection.filingsSymbol ??
      searchSelection.newsSymbol ??
      searchSelection.discoveryQuery;

    if (symbol) {
      const normalized = symbol.toUpperCase();
      setActiveSymbol(normalized);
      setSymbolInput(normalized);
    }

    if (searchSelection.companyId) {
      setActiveCompanyId(searchSelection.companyId);
    } else {
      setActiveCompanyId(null);
    }

    if (
      searchSelection.reportScope === "comparison" &&
      searchSelection.reportCompareSymbols?.length
    ) {
      const normalized = searchSelection.reportCompareSymbols
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 4);

      if (normalized.length >= 2) {
        if (normalized.length >= 2) {
          const symbolsText = normalized.join(" vs ");

          setReportScope("comparison");
          setComparisonSymbols(normalized);
          setComparisonSymbolsInput(normalized.join(", "));
          setReportTitle(`${symbolsText} Comparative Brief`);
          setReportSections(["summary", "risks", "financials", "themes"]);
          setReportAudience("analyst");
          setReportGeneratedAt(new Date().toISOString());

          pushToast("Comparison report draft generated", "success");
        }
      }
    } else if (searchSelection.reportScope === "company") {
      setReportScope("company");
      setComparisonSymbols([]);
      setComparisonSymbolsInput("");
    }

    setLastSelectionStamp(searchSelection.stamp);
  }, [lastSelectionStamp, pushToast, searchSelection]);

  const [companyDetail, setCompanyDetail] = useState<AICompany | null>(null);
  const [companyQuote, setCompanyQuote] = useState<AIQuote | null>(null);
  const [companyRatios, setCompanyRatios] = useState<AIRatios | null>(null);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyTimeline, setCompanyTimeline] = useState<BackendTimelineEvent[]>([]);

  const loadCompanyById = useCallback(async (companyId: string) => {
    setCompanyLoading(true);
    try {
      const [detail, ratios] = await Promise.allSettled([
        fetchCompanyDetail(companyId),
        fetchCompanyRatios(companyId),
      ]);
      let detailData: AICompany | null = null;
      if (detail.status === "fulfilled") {
        detailData = detail.value;
        setCompanyDetail(detailData);
      }
      if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
      fetchCompanyQuote(companyId).then(setCompanyQuote).catch(() => {});
      fetchTimeline(undefined, companyId, 10).then(setCompanyTimeline).catch(() => {});

      if (detailData && !detailData.sector) {
        enrichCompany(companyId).then(async (res) => {
          if (res.enriched) {
            const refreshed = await fetchCompanyDetail(companyId);
            setCompanyDetail(refreshed);
          }
        }).catch(() => {});
      }
    } catch {
      // Ignore lookup failures; UI shows fallback messaging.
    } finally {
      setCompanyLoading(false);
    }
  }, []);

  const loadCompanyBySymbol = useCallback(async (symbol: string) => {
    setCompanyLoading(true);
    try {
      const results = await searchCompaniesDB(symbol, 5);
      if (results.length > 0) {
        const matched = results[0];
        const [detail, ratios] = await Promise.allSettled([
          fetchCompanyDetail(matched.id),
          fetchCompanyRatios(matched.id),
        ]);
        let detailData: AICompany | null = null;
        if (detail.status === "fulfilled") {
          detailData = detail.value;
          setCompanyDetail(detailData);
        }
        if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
        fetchCompanyQuote(matched.id).then(setCompanyQuote).catch(() => {});
        fetchTimeline(undefined, matched.id, 10).then(setCompanyTimeline).catch(() => {});

        if (detailData && !detailData.sector) {
          enrichCompany(matched.id).then(async (res) => {
            if (res.enriched) {
              const refreshed = await fetchCompanyDetail(matched.id);
              setCompanyDetail(refreshed);
            }
          }).catch(() => {});
        }
      }
    } catch {
      // Ignore lookup failures; UI shows fallback messaging.
    } finally {
      setCompanyLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeCompanyId) {
      void loadCompanyById(activeCompanyId);
    } else {
      void loadCompanyBySymbol(activeSymbol);
    }
  }, [activeSymbol, activeCompanyId, loadCompanyById, loadCompanyBySymbol]);

  const companyData = useMemo((): DiscoveryCompany => {
    if (companyDetail) {
      const mcBn = companyDetail.market_cap_inr ? companyDetail.market_cap_inr / 1e9 : 0;
      const ticker = companyDetail.ticker_nse ?? companyDetail.ticker_bse;
      const symbol = ticker ?? companyDetail.name;
      return {
        symbol,
        name: companyDetail.name,
        sector: companyDetail.sector ?? "Unknown",
        marketCapBn: mcBn,
        insight: companyDetail.description ?? companyDetail.industry ?? "",
        themeScores: {},
      };
    }
    return {
      symbol: activeSymbol,
      name: `${activeSymbol}`,
      sector: "Unknown",
      marketCapBn: 0,
      insight: companyLoading ? "Loading company data..." : "Search for a company by ticker or name.",
      themeScores: {},
    };
  }, [activeSymbol, companyDetail, companyLoading]);

  const topThemes = useMemo(
    () => Object.entries(companyData.themeScores).sort((a, b) => b[1] - a[1]).slice(0, 5),
    [companyData.themeScores]
  );

  const comparisonCompanies = useMemo(() => {
    if (reportScope !== "comparison") return [];
    return comparisonSymbols.map((symbol) => ({
      symbol,
      name: symbol,
      sector: "Unknown",
      marketCapBn: 0,
      insight: "",
      themeScores: {},
    } as DiscoveryCompany));
  }, [comparisonSymbols, reportScope]);

  const comparisonTimeline = useMemo((): TimelineEvent[] => {
    if (reportScope !== "comparison") return [];
    return [];
  }, [reportScope]);

  const comparisonMetrics = useMemo(() => {
    if (reportScope !== "comparison" || comparisonCompanies.length < 2) {
      return null;
    }

    const strengths = comparisonCompanies.map((company) => {
      const [theme, score] = Object.entries(company.themeScores).sort((a, b) => b[1] - a[1])[0] ?? ["None", 0];
      return { symbol: company.symbol, topTheme: theme, score };
    });

    const strongest = strengths.reduce((best, current) =>
      !best || current.score > best.score ? current : best
    );
    const weakest = strengths.reduce((worst, current) =>
      !worst || current.score < worst.score ? current : worst
    );

    const riskScores = comparisonCompanies.map((company) => {
      const avg =
        Object.values(company.themeScores).reduce((sum, value) => sum + value, 0) /
        Math.max(Object.values(company.themeScores).length, 1);
      const concentrationPenalty = Math.max(0, 90 - avg);
      const timelinePenalty = comparisonTimeline.filter(
        (event) => event.company === company.symbol && event.impact === "high"
      ).length;

      return {
        symbol: company.symbol,
        score: Number((concentrationPenalty + timelinePenalty * 4).toFixed(1)),
      };
    });

    const highestRisk = riskScores.reduce((best, current) =>
      !best || current.score > best.score ? current : best
    );
    const lowestRisk = riskScores.reduce((best, current) =>
      !best || current.score < best.score ? current : best
    );

    const allThemesSet = new Set<string>();
    comparisonCompanies.forEach((company) => {
      Object.keys(company.themeScores).forEach((theme) => allThemesSet.add(theme));
    });

    const divergence = Array.from(allThemesSet)
      .map((theme) => {
        const values = comparisonCompanies.map((company) => company.themeScores[theme] ?? 0);
        const spread = Math.max(...values) - Math.min(...values);
        return { theme, spread };
      })
      .sort((a, b) => b.spread - a.spread)
      .slice(0, 3);

    return {
      strengths,
      strongest,
      weakest,
      highestRisk,
      lowestRisk,
      divergence,
    };
  }, [comparisonCompanies, comparisonTimeline, reportScope]);

  const [companyFilings, setCompanyFilings] = useState<(SecFiling & { narrative: string })[]>([]);

  const filingsTicker = companyDetail?.ticker_nse ?? null;

  useEffect(() => {
    if (dataMode === "demo" || !filingsTicker) {
      setCompanyFilings([]);
      return;
    }
    fetchSecFilings(filingsTicker, 7).then((filings) => {
      setCompanyFilings(filings.slice(0, 7).map((f) => ({
        ...f,
        narrative: f.type === "10-K"
          ? "Annual report and strategic commentary."
          : f.type === "10-Q"
            ? "Quarterly operating metrics and margin data."
            : "Event or regulatory disclosure.",
      })));
    }).catch(() => setCompanyFilings([]));
  }, [filingsTicker, dataMode]);

  const companyRatioSnapshot = useMemo(() => {
    if (companyRatios?.ratios) {
      const r = companyRatios.ratios;
      return {
        pe: r.pe_ratio ?? 0,
        pb: r.pb_ratio ?? 0,
        roe: r.roe ?? 0,
        debtToEquity: r.debt_to_equity ?? 0,
        operatingMargin: r.ebitda_margin ?? r.net_margin ?? 0,
        beta: 1.0,
      };
    }
    return { pe: 0, pb: 0, roe: 0, debtToEquity: 0, operatingMargin: 0, beta: 0 };
  }, [companyRatios]);

  const companySentimentTrend = useMemo(() => {
    const topThemeScore = topThemes[0]?.[1] ?? 62;
    const baseShift = Math.round((topThemeScore - 60) / 7);
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    return days.map((day, index) => {
      const positive = Math.max(1, 5 + baseShift + ((index + 2) % 3));
      const negative = Math.max(0, 2 + ((index + 1) % 2) - Math.max(baseShift, -1));
      const neutral = Math.max(1, 7 - index + Math.max(0, baseShift));
      const score = positive * 2 + neutral - negative * 2;

      return {
        day,
        positive,
        neutral,
        negative,
        score,
      };
    });
  }, [topThemes]);

  const companyLabel = companyData.name !== companyData.symbol ? companyData.name : companyData.symbol;

  const tabPrompts = useMemo<Record<"overview" | "filings" | "sentiment" | "timeline" | "chat", string[]>>(
    () => ({
      overview: [
        `Give a 5-point briefing on ${companyLabel} strategic posture.`,
        `What three catalysts should I monitor for ${companyLabel}?`,
        `Summarize valuation context for ${companyLabel} in plain terms.`,
      ],
      filings: [
        `What changed materially in ${companyLabel} recent filings?`,
        `List potential red flags from ${companyLabel} latest disclosures.`,
        `Convert ${companyLabel} filing updates into an action checklist.`,
      ],
      sentiment: [
        `How stable is ${companyLabel} sentiment trend this week?`,
        `Explain the sentiment shift in ${companyLabel} with likely drivers.`,
        `What sentiment reversal signals should I watch for ${companyLabel}?`,
      ],
      timeline: [
        `Rank ${companyLabel} timeline events by decision relevance.`,
        `What is the most important recent event for ${companyLabel} and why?`,
        `Build a risk-aware timeline summary for ${companyLabel}.`,
      ],
      chat: [
        `Prepare a balanced bull vs bear case for ${companyLabel}.`,
        `What should I verify before increasing exposure to ${companyLabel}?`,
        `Create a one-week monitoring plan for ${companyLabel}.`,
      ],
    }),
    [companyLabel]
  );

  const [companyChatPrompt, setCompanyChatPrompt] = useState("");

  useEffect(() => {
    const first = tabPrompts[activeTab]?.[0] ?? "";
    setCompanyChatPrompt(first);
  }, [activeTab, tabPrompts]);

  const comparisonSummary = useMemo(() => {
    if (reportScope !== "comparison" || comparisonCompanies.length < 2 || !comparisonMetrics) {
      return null;
    }

    const avgMarketCap =
      comparisonCompanies.reduce((sum, company) => sum + company.marketCapBn, 0) /
      comparisonCompanies.length;
    const sectors = Array.from(new Set(comparisonCompanies.map((company) => company.sector))).join(", ");

    return {
      symbolsLabel: comparisonCompanies.map((company) => company.symbol).join(" vs "),
      avgMarketCap,
      sectors,
      topSpreadTheme: comparisonMetrics.divergence[0],
    };
  }, [comparisonCompanies, comparisonMetrics, reportScope]);

  const nseOrBseTicker = companyDetail?.ticker_nse ?? companyDetail?.ticker_bse;
  const profileTitle = nseOrBseTicker
    ? `${nseOrBseTicker} · ${companyData.name}`
    : companyData.name;

  const generatedReport = useMemo<GeneratedReport | null>(() => {
    if (!reportGeneratedAt) return null;

    const sections: GeneratedReportSection[] = [];

    if (reportScope === "comparison" && (!comparisonSummary || !comparisonMetrics)) {
      return null;
    }

    if (reportScope === "comparison" && comparisonSummary && comparisonMetrics) {
      if (reportSections.includes("summary")) {
        sections.push({
          id: "summary",
          heading: "Executive Summary",
          content:
            `${comparisonSummary.symbolsLabel} comparison indicates strongest momentum in ` +
            `${comparisonMetrics.strongest.symbol} (${comparisonMetrics.strongest.topTheme} ${comparisonMetrics.strongest.score}/100), ` +
            `while ${comparisonMetrics.weakest.symbol} trails on composite theme intensity (${comparisonMetrics.weakest.score}/100).`,
        });
      }

      if (reportSections.includes("risks")) {
        const riskSpread = (comparisonMetrics.highestRisk.score - comparisonMetrics.lowestRisk.score).toFixed(
          1
        );
        sections.push({
          id: "risks",
          heading: "Risk Spread",
          content:
            `Highest modeled risk: ${comparisonMetrics.highestRisk.symbol} (${comparisonMetrics.highestRisk.score}).\n` +
            `Lowest modeled risk: ${comparisonMetrics.lowestRisk.symbol} (${comparisonMetrics.lowestRisk.score}).\n` +
            `Spread: ${riskSpread}. Monitor names with weaker average theme quality and clustered high-impact events.`,
        });
      }

      if (reportSections.includes("financials")) {
        const winnersText = [...comparisonCompanies]
          .sort((a, b) => b.marketCapBn - a.marketCapBn)
          .slice(0, 2)
          .map((company) => `${company.symbol} ($${company.marketCapBn.toFixed(1)}B)`)
          .join(", ");

        sections.push({
          id: "financials",
          heading: "Scale & Coverage",
          content:
            `Average market cap across basket: $${comparisonSummary.avgMarketCap.toFixed(1)}B.\n` +
            `Largest names by scale: ${winnersText}.\n` +
            `Sector mix: ${comparisonSummary.sectors}.`,
        });
      }

      if (reportSections.includes("themes")) {
        const divergenceText = comparisonMetrics.divergence.length
          ? comparisonMetrics.divergence
              .map((item) => `${item.theme} (spread ${item.spread})`)
              .join(", ")
          : "No meaningful divergence detected";

        sections.push({
          id: "themes",
          heading: "Theme Divergence",
          content:
            `${divergenceText}.\n` +
            `Largest current gap: ${comparisonSummary.topSpreadTheme?.theme ?? "N/A"} ` +
            `(${comparisonSummary.topSpreadTheme?.spread ?? 0} points).`,
        });
      }

      const audienceText =
        reportAudience === "retail"
          ? "Retail framing: prefer simple winner/laggard interpretation and avoid overtrading on one-cycle noise."
          : "Analyst framing: evaluate relative momentum, dispersion, and event-adjusted risk asymmetry across the basket.";

      return {
        title: reportTitle.trim() || `${comparisonSummary.symbolsLabel} Comparative Brief`,
        generatedAt: reportGeneratedAt,
        audience: reportAudience,
        audienceText,
        symbol: comparisonSummary.symbolsLabel,
        companyName: "Comparison Basket",
        dataMode,
        scope: "comparison",
        compareSymbols: comparisonCompanies.map((company) => company.symbol),
        sections,
        body: sections.map((section) => `${section.heading}:\n${section.content}`).join("\n\n"),
      };
    }

    const topTheme = topThemes[0]?.[0] ?? "No clear dominant theme";
    const topThemeScore = topThemes[0]?.[1] ?? 0;

    if (reportSections.includes("summary")) {
      sections.push({
        id: "summary",
        heading: "Executive Summary",
        content: `${companyData.name}${nseOrBseTicker ? ` (${nseOrBseTicker})` : ""} currently shows strongest narrative strength in ${topTheme} with theme score ${topThemeScore}/100. Sector context remains ${companyData.sector}.`,
      });
    }

    if (reportSections.includes("risks")) {
      sections.push({
        id: "risks",
        heading: "Key Risks",
        content:
          "1) Execution risk around near-term filings guidance.\n2) Valuation sensitivity if sector momentum cools.\n3) Sentiment volatility around macro updates.",
      });
    }

    if (reportSections.includes("financials")) {
      sections.push({
        id: "financials",
        heading: "Financial Snapshot",
        content: `Market Cap: $${companyData.marketCapBn.toFixed(1)}B\nRecent timeline events: ${companyTimeline.length}\nPrimary sector: ${companyData.sector}`,
      });
    }

    if (reportSections.includes("themes")) {
      const themeText = topThemes.length
        ? topThemes.map(([theme, score]) => `${theme} (${score})`).join(", ")
        : "No theme signal available";

      sections.push({
        id: "themes",
        heading: "Theme Outlook",
        content: `Dominant theme signals: ${themeText}.`,
      });
    }

    const audienceText =
      reportAudience === "retail"
        ? "Retail framing: keep explanations concise and action oriented."
        : "Analyst framing: include context, assumptions, and scenario sensitivity.";

    return {
      title: reportTitle.trim() || `${companyLabel} Research Brief`,
      generatedAt: reportGeneratedAt,
      audience: reportAudience,
      audienceText,
      symbol: companyData.symbol,
      companyName: companyData.name,
      dataMode,
      scope: "company",
      sections,
      body: sections
        .map((section) => `${section.heading}:\n${section.content}`)
        .join("\n\n"),
    };
  }, [
    comparisonCompanies,
    comparisonMetrics,
    comparisonSummary,
    companyData.marketCapBn,
    companyData.name,
    companyData.sector,
    companyData.symbol,
    companyTimeline.length,
    reportScope,
    reportAudience,
    reportGeneratedAt,
    reportSections,
    reportTitle,
    companyLabel,
    nseOrBseTicker,
    dataMode,
    topThemes,
  ]);

  const toggleReportSection = (sectionId: ReportSectionId) => {
    setReportSections((current) => {
      if (current.includes(sectionId)) {
        const next = current.filter((id) => id !== sectionId);
        return next.length ? next : current;
      }
      return [...current, sectionId];
    });
  };

  const triggerReportGeneration = () => {
    if (reportScope === "comparison") {
      const normalized = normalizeSymbolsInput(comparisonSymbolsInput || comparisonSymbols.join(","));
      if (normalized.length >= 2) {
        setComparisonSymbols(normalized);
        setComparisonSymbolsInput(normalized.join(", "));
      }

      if (normalized.length < 2) {
        pushToast("Comparison report needs at least two valid symbols", "warning");
        return;
      }
    }
    setReportGeneratedAt(new Date().toISOString());
  };

  const exportReportAsText = () => {
    if (!generatedReport) return;

    const payload = [
      generatedReport.title,
      `Generated: ${new Date(generatedReport.generatedAt).toLocaleString()}`,
      generatedReport.audienceText,
      "",
      generatedReport.body,
    ].join("\n");

    const blob = new Blob([payload], { type: "text/plain;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    const baseName = generatedReport.scope === "comparison" ? generatedReport.symbol : companyLabel;
    anchor.download = `${toFileSlug(baseName)}-report.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
    pushToast("Text report downloaded", "success");
  };

  const exportReportPdf = async () => {
    if (!generatedReport) return;
    try {
      pushToast("Preparing PDF export...", "info");
      await exportReportAsPdf(generatedReport);
      pushToast("PDF report downloaded", "success");
    } catch {
      pushToast("PDF export failed. Please try again.", "warning");
    }
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Company Workspace"
        subtitle="One research cockpit per company: filings, sentiment, timeline, and company-context chat."
        dataMode={dataMode}
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              const normalized = symbolInput.trim().toUpperCase();
              if (normalized) {
                setActiveCompanyId(null);
                setActiveSymbol(normalized);
              }
            }}
          >
            <Search size={14} />
            <input
              placeholder="Enter company symbol"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
            />
          </form>
        }
      />

      {reportScope === "comparison" && comparisonSummary ? (
        <div className="notice">
          Comparison report mode: {comparisonSummary.symbolsLabel}. Generate a unified winner/laggard and
          risk-spread brief from this basket.
        </div>
      ) : null}

      {companyLoading && <div className="notice"><Loader2 size={16} className="spin" /> Loading company data...</div>}

      <div className="company-header-card">
        <div className="company-header-main">
          {nseOrBseTicker && <p className="discovery-symbol">{nseOrBseTicker}</p>}
          <h2>{companyData.name}</h2>
          <p>{companyData.insight}</p>
          <div className="chip-row">
            <span className="chip">Sector: {companyData.sector}</span>
            {companyData.marketCapBn > 0 && <span className="chip">Market Cap: ₹{companyData.marketCapBn.toFixed(1)}B</span>}
          </div>
          <SourceBadges sources={companyDetail?.data_sources} />
        </div>
        <div className="company-header-actions">
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() =>
              props.addFavorite({
                type: "company",
                symbol: companyData.symbol,
                title: profileTitle,
                subtitle: companyData.insight,
              })
            }
          >
            {props.isFavorited({ type: "company", symbol: companyData.symbol, title: profileTitle }) ? (
              <>
                <BookmarkCheck size={14} />
                Saved
              </>
            ) : (
              <>
                <Bookmark size={14} />
                Save Company
              </>
            )}
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => {
              setActiveTab("chat");
            }}
          >
            <ArrowUpRight size={14} />
            Ask Iris
          </button>
        </div>
      </div>

      <div className="company-tabs">
        {[
          ["overview", "Overview"],
          ["filings", "Filings"],
          ["sentiment", "Sentiment"],
          ["timeline", "Timeline"],
          ["chat", "Chat"],
        ].map(([tabId, label]) => (
          <button
            key={tabId}
            type="button"
            className={`company-tab-btn ${activeTab === tabId ? "active" : ""}`}
            onClick={() => setActiveTab(tabId as typeof activeTab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" ? (
        <div className="split-grid">
          <article className="feature-card">
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Live Quote</h3>
            </div>
            {companyQuote?.last_price ? (
              <>
                <h2>₹{Number(companyQuote.last_price).toLocaleString()}</h2>
                {companyQuote.change_pct != null && (
                  <p className={Number(companyQuote.change_pct) >= 0 ? "positive" : "negative"}>
                    {Number(companyQuote.change_pct) >= 0 ? "+" : ""}{Number(companyQuote.change_pct).toFixed(2)}%
                  </p>
                )}
                <small>Source: {companyQuote.source ?? "API"} · {companyQuote.fetched_at ? new Date(companyQuote.fetched_at).toLocaleTimeString() : ""}</small>
                <SourceBadges sources={companyQuote.data_sources} />
              </>
            ) : (
              <p>{companyLoading ? "Fetching quote..." : "No live quote data available."}</p>
            )}
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <Clock3 size={18} />
              <h3>Recent Events</h3>
            </div>
            <p>{companyTimeline.length} recent timeline events for this company.</p>
            {companyTimeline.slice(0, 3).map((ev) => (
              <div key={ev.id} className="list-item">
                <p>{ev.title}</p>
                <small>{new Date(ev.timestamp).toLocaleDateString()}</small>
              </div>
            ))}
          </article>
        </div>
      ) : null}

      {activeTab === "filings" ? (
        <article className="list-card company-filings-card">
          <div className="table-head">
            <h3>Filings Snapshot ({companyLabel})</h3>
            <span>{companyFilings.length} filings</span>
          </div>
          {companyFilings.map((filing, index) => (
            <div key={`${filing.type}-${filing.filingDate ?? index}`} className="list-item company-filing-row">
              <div>
                <p>{filing.type} · {filing.title}</p>
                <small>{filing.narrative}</small>
              </div>
              <span>{new Date(filing.filingDate ?? filing.acceptedDate ?? Date.now()).toLocaleDateString()}</span>
            </div>
          ))}
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => {
              props.setSearchSelection({
                stamp: Date.now(),
                filingsSymbol: companyData.symbol,
                companySymbol: companyData.symbol,
              });
              props.goToView("filings");
            }}
          >
            Open Full Filings Workspace
          </button>
        </article>
      ) : null}

      {activeTab === "sentiment" ? (
        <div className="split-grid">
          <article className="feature-card">
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Sentiment Timeline ({companyLabel})</h3>
            </div>
            <div className="chart-wrap medium">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={companySentimentTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,132,145,0.22)" />
                  <XAxis dataKey="day" tick={{ fill: "#7d8792", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#7d8792", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid rgba(120,132,145,0.25)",
                      background: "rgba(12,18,26,0.92)",
                      color: "#e8edf2",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#139bcf"
                    strokeWidth={2.2}
                    dot={{ r: 2.8, fill: "#139bcf" }}
                    name="Net Sentiment"
                  />
                  <Line
                    type="monotone"
                    dataKey="negative"
                    stroke="#d86c52"
                    strokeWidth={1.6}
                    dot={false}
                    name="Negative Mentions"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>Ratio Snapshot ({companyLabel})</h3>
            </div>
            <SourceBadges sources={companyRatios?.data_sources} />
            <div className="ratio-grid">
              <div className="ratio-item">
                <span>PE</span>
                <strong>{companyRatioSnapshot.pe.toFixed(1)}</strong>
              </div>
              <div className="ratio-item">
                <span>PB</span>
                <strong>{companyRatioSnapshot.pb.toFixed(2)}</strong>
              </div>
              <div className="ratio-item">
                <span>ROE</span>
                <strong>{companyRatioSnapshot.roe.toFixed(1)}%</strong>
              </div>
              <div className="ratio-item">
                <span>Debt/Equity</span>
                <strong>{companyRatioSnapshot.debtToEquity.toFixed(2)}</strong>
              </div>
              <div className="ratio-item">
                <span>Op Margin</span>
                <strong>{companyRatioSnapshot.operatingMargin.toFixed(1)}%</strong>
              </div>
              <div className="ratio-item">
                <span>Beta</span>
                <strong>{companyRatioSnapshot.beta.toFixed(2)}</strong>
              </div>
            </div>
          </article>
        </div>
      ) : null}

      {activeTab === "timeline" ? (
        <article className="list-card">
          {companyTimeline.length ? (
            companyTimeline.map((event) => (
              <div key={event.id} className="list-item">
                <p>{event.title}</p>
                <span>{new Date(event.timestamp).toLocaleString()}</span>
              </div>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No timeline events for {companyLabel} in local dataset.</p>
            </div>
          )}
        </article>
      ) : null}

      {activeTab === "chat" ? (
        <article className="chat-shell">
          <div className="chat-suggestions">
            {tabPrompts[activeTab].map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="chat-suggestion-chip"
                onClick={() => setCompanyChatPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
          <div className="chat-messages">
            <div className="message assistant">
              <p>
                You are now in {companyLabel} context. Ask company-specific questions to get
                tighter research answers.
              </p>
              <div className="source-list">
                <span className="source-chip">Company Workspace · Context mode</span>
              </div>
            </div>
          </div>
          <div className="chat-input-row">
            <input
              value={companyChatPrompt}
              onChange={(event) => setCompanyChatPrompt(event.target.value)}
            />
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                if (!companyChatPrompt.trim()) return;
                props.setSearchSelection({
                  stamp: Date.now(),
                  companySymbol: companyData.symbol,
                  chatPrompt: companyChatPrompt,
                });
                props.goToView("chat");
              }}
            >
              Ask in Iris Chat
            </button>
          </div>
        </article>
      ) : null}

      {activeTab !== "chat" ? (
        <article className="feature-card tab-prompt-card">
          <div className="feature-head">
            <Bot size={18} />
            <h3>Contextual Prompts for {activeTab[0].toUpperCase() + activeTab.slice(1)}</h3>
          </div>
          <div className="chat-suggestions">
            {tabPrompts[activeTab].map((prompt) => (
              <button
                key={`${activeTab}-${prompt}`}
                type="button"
                className="chat-suggestion-chip"
                onClick={() => {
                  props.setSearchSelection({
                    stamp: Date.now(),
                    companySymbol: companyData.symbol,
                    chatPrompt: prompt,
                  });
                  props.goToView("chat");
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </article>
      ) : null}

      <article className="report-builder-card">
        <div className="feature-head">
          <FileText size={18} />
          <h3>Report Generation Workspace</h3>
        </div>

        <div className="report-scope-row">
          <button
            type="button"
            className={`mode-pill ${reportScope === "company" ? "active" : ""}`}
            onClick={() => {
              setReportScope("company");
              setComparisonSymbols([]);
              setComparisonSymbolsInput("");
            }}
          >
            Company Report
          </button>
          <button
            type="button"
            className={`mode-pill ${reportScope === "comparison" ? "active" : ""}`}
            onClick={() => {
              const normalized = normalizeSymbolsInput(
                comparisonSymbolsInput || comparisonSymbols.join(",") || `${activeSymbol}, TCS`
              );
              if (normalized.length >= 2) {
                setComparisonSymbols(normalized);
                setComparisonSymbolsInput(normalized.join(", "));
                setReportScope("comparison");
                setReportTitle(`${normalized.join(" vs ")} Comparative Brief`);
              } else {
                pushToast("Add at least two symbols for comparison report", "warning");
              }
            }}
          >
            Comparison Report
          </button>
        </div>

        {reportScope === "comparison" ? (
          <div className="report-builder-grid">
            <label className="report-field">
              <span>Comparison symbols</span>
              <input
                value={comparisonSymbolsInput || comparisonSymbols.join(", ")}
                readOnly
              />
            </label>
            <label className="report-field">
              <span>Comparison focus</span>
              <input
                value={comparisonSummary ? `${comparisonSummary.symbolsLabel}` : "No valid basket yet"}
                readOnly
              />
            </label>
          </div>
        ) : null}

        {reportScope === "comparison" && comparisonMetrics ? (
          <div className="comparison-report-insights">
            <div className="chip-row">
              <span className="chip">Winner: {comparisonMetrics.strongest.symbol}</span>
              <span className="chip">Laggard: {comparisonMetrics.weakest.symbol}</span>
              <span className="chip warning">Risk High: {comparisonMetrics.highestRisk.symbol}</span>
              <span className="chip positive">Risk Low: {comparisonMetrics.lowestRisk.symbol}</span>
            </div>
          </div>
        ) : null}

        <div className="report-builder-grid">
          <label className="report-field">
            <span>Report title</span>
            <input
              value={reportTitle}
              onChange={(event) => setReportTitle(event.target.value)}
              placeholder={`${companyLabel} quarterly research brief`}
            />
          </label>

          <label className="report-field">
            <span>Audience</span>
            <select
              className="type-select"
              value={reportAudience}
              onChange={(event) => setReportAudience(event.target.value as ReportAudience)}
            >
              <option value="analyst">Analyst</option>
              <option value="retail">Retail</option>
            </select>
          </label>
        </div>

        <div className="chip-row report-section-chips">
          {REPORT_SECTION_OPTIONS.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`widget-toggle-chip ${reportSections.includes(section.id) ? "active" : ""}`}
              onClick={() => toggleReportSection(section.id)}
            >
              {section.label}
            </button>
          ))}
        </div>

        <div className="report-action-row">
          <button type="button" className="primary-btn" onClick={triggerReportGeneration}>
            Generate Report
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={exportReportAsText}
            disabled={!generatedReport}
          >
            Download .txt
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={exportReportPdf}
            disabled={!generatedReport}
          >
            Download .pdf
          </button>
        </div>

        {generatedReport ? (
          <div className="report-preview">
            <h4>{generatedReport.title}</h4>
            <p>{generatedReport.audienceText}</p>
            <small>Scope: {generatedReport.scope === "comparison" ? "Comparison" : "Company"}</small>
            <small>
              Template: {generatedReport.audience === "retail" ? "Retail Brief" : "Analyst Dossier"}
            </small>
            <small>Generated: {new Date(generatedReport.generatedAt).toLocaleString()}</small>
            <pre>{generatedReport.body}</pre>
          </div>
        ) : (
          <p className="report-placeholder">
            Select sections and click Generate Report to build a company-specific brief.
          </p>
        )}
      </article>
    </section>
  );
}
