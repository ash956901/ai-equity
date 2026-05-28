import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUpRight,
  BarChart3,
  Bookmark,
  BookmarkCheck,
  Bot,
  Clock3,
  FileText,
  Loader2,
  RefreshCw,
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
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Filler,
  Title as ChartTitle,
  Tooltip as ChartTooltip,
  Legend as ChartLegend,
} from 'chart.js';
import { Bar, Line as ChartLine } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Filler,
  ChartTitle,
  ChartTooltip,
  ChartLegend
);

import {
  compareCompanies,
  fetchSecFilings,
  fetchCompanyDetail,
  fetchCompanyRatios,
  fetchCompanyQuote,
  fetchCompanyFinancials,
  fetchHistoricalPrices,
  searchCompaniesDB,
  fetchTimeline,
  enrichCompany,
  sendChatQuery,
  type SecFiling,
  type AICompany,
  type AIRatios,
  type AIQuote,
  type AIFinancials,
  type AIHistoricalPrices,
  type TimelineEvent as BackendTimelineEvent,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { SourceBadges } from "../../shared/ui/SourceBadges";
import { CompanySearchInput } from "../../shared/components/CompanySearchInput";

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

interface CompareResultSnapshot {
  companyA_summary: string;
  companyB_summary: string;
  comparison: {
    growth: "A" | "B" | "Tie";
    profitability: "A" | "B" | "Tie";
    risk: "A" | "B" | "Tie";
    valuation: "A" | "B" | "Tie";
  };
  insights: string[];
  final_verdict: string;
  detailed_comparison: Record<string, string>;
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

interface PdfExtraData {
  lastPrice?: number | null;
  changePct?: number | null;
  pe?: number; pb?: number; roe?: number; debtToEquity?: number; operatingMargin?: number; beta?: number;
  priceHistory?: { date: string; close: number }[];
}

async function exportReportAsPdf(
  report: GeneratedReport,
  bodyOverride?: string | null,
  extra?: PdfExtraData
): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  const ML = 14;
  const MR = W - 14;
  const CW = MR - ML;
  const template = PDF_TEMPLATES[report.audience];
  const [ar, ag, ab] = template.accent;

  const checkPage = (needed: number) => {
    if (y + needed > H - 18) { doc.addPage(); y = 18; }
  };

  // ── Cover banner ──────────────────────────────────────────────────────────
  doc.setFillColor(ar, ag, ab);
  doc.rect(0, 0, W, 52, "F");
  // decorative strip
  doc.setFillColor(Math.max(ar - 20, 0), Math.max(ag - 20, 0), Math.max(ab - 20, 0));
  doc.rect(0, 46, W, 6, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.text("EQUITYAI RESEARCH PLATFORM", ML, 12);
  doc.setFontSize(22);
  doc.text(report.companyName, ML, 25);
  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");
  doc.text(`${report.symbol}   ·   ${template.coverLabel}`, ML, 33);

  // Stock price badge (right side of banner)
  if (extra?.lastPrice) {
    const priceStr = `₹${Number(extra.lastPrice).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
    const changeStr = extra.changePct != null
      ? `  ${extra.changePct >= 0 ? "▲" : "▼"} ${Math.abs(extra.changePct).toFixed(2)}%`
      : "";
    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.text(priceStr, MR - 40, 22, { align: "right" });
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(extra.changePct != null && extra.changePct >= 0 ? 120 : 255, 230, extra.changePct != null && extra.changePct >= 0 ? 255 : 120);
    doc.text(changeStr, MR - 40, 30, { align: "right" });
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(8);
    doc.text("Live Price", MR - 40, 37, { align: "right" });
  }

  // Timestamp row
  doc.setTextColor(200, 220, 240);
  doc.setFontSize(8);
  const genDate = new Date().toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
  doc.text(`Generated: ${genDate} IST   ·   Audience: ${report.audience === "retail" ? "Retail" : "Analyst"}   ·   Data: ${report.dataMode === "demo" ? "Demo" : "Live"}`, ML, 42);

  let y = 62;

  // ── Sparkline (30-day price trend) ───────────────────────────────────────
  if (extra?.priceHistory && extra.priceHistory.length > 3) {
    const prices = extra.priceHistory;
    const chartX = ML;
    const chartY = y;
    const chartW = CW;
    const chartH = 28;

    const vals = prices.map(p => p.close);
    const minVal = Math.min(...vals);
    const maxVal = Math.max(...vals);
    const range = maxVal - minVal || 1;

    // Chart background
    doc.setFillColor(245, 248, 252);
    doc.setDrawColor(220, 228, 236);
    doc.roundedRect(chartX, chartY, chartW, chartH, 2, 2, "FD");

    // Title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(ar, ag, ab);
    doc.text("30-DAY PRICE TREND", chartX + 3, chartY + 5);

    // Min/Max labels
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(80, 80, 80);
    doc.text(`H: ₹${maxVal.toFixed(0)}`, MR - 3, chartY + 5, { align: "right" });
    doc.text(`L: ₹${minVal.toFixed(0)}`, MR - 3, chartY + 11, { align: "right" });

    // Draw sparkline
    const plotX = chartX + 3;
    const plotW = chartW - 30;
    const plotY = chartY + chartH - 5;
    const plotH = chartH - 12;

    const lastClose = vals[vals.length - 1];
    const firstClose = vals[0];
    const isUp = lastClose >= firstClose;
    doc.setDrawColor(isUp ? 34 : 220, isUp ? 197 : 53, isUp ? 94 : 69);

    for (let i = 1; i < vals.length; i++) {
      const x1 = plotX + ((i - 1) / (vals.length - 1)) * plotW;
      const x2 = plotX + (i / (vals.length - 1)) * plotW;
      const y1 = plotY - ((vals[i - 1] - minVal) / range) * plotH;
      const y2 = plotY - ((vals[i] - minVal) / range) * plotH;
      doc.line(x1, y1, x2, y2);
    }

    // Current price dot
    const lastX = plotX + plotW;
    const lastY = plotY - ((lastClose - minVal) / range) * plotH;
    doc.setFillColor(isUp ? 34 : 220, isUp ? 197 : 53, isUp ? 94 : 69);
    doc.circle(lastX, lastY, 1, "F");

    y += chartH + 6;
  }

  // ── Key Ratios table ──────────────────────────────────────────────────────
  if (extra && (extra.pe || extra.pb || extra.roe)) {
    checkPage(28);
    const tableX = ML;
    const tableY = y;
    const colW = CW / 6;

    // Header bar
    doc.setFillColor(ar, ag, ab);
    doc.rect(tableX, tableY, CW, 7, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    const headers = ["P/E", "P/B", "ROE", "D/E", "Op. Margin", "Beta"];
    headers.forEach((h, i) => {
      doc.text(h, tableX + colW * i + colW / 2, tableY + 4.8, { align: "center" });
    });

    // Values row
    doc.setFillColor(245, 248, 252);
    doc.rect(tableX, tableY + 7, CW, 9, "F");
    doc.setDrawColor(220, 228, 236);
    doc.rect(tableX, tableY, CW, 16, "D");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.setTextColor(18, 32, 45);
    const values = [
      extra.pe ? extra.pe.toFixed(1) : "—",
      extra.pb ? extra.pb.toFixed(2) : "—",
      extra.roe ? `${extra.roe.toFixed(1)}%` : "—",
      extra.debtToEquity ? extra.debtToEquity.toFixed(2) : "—",
      extra.operatingMargin ? `${extra.operatingMargin.toFixed(1)}%` : "—",
      extra.beta ? extra.beta.toFixed(2) : "—",
    ];
    values.forEach((v, i) => {
      doc.text(v, tableX + colW * i + colW / 2, tableY + 13, { align: "center" });
    });

    // Column dividers
    doc.setDrawColor(210, 218, 228);
    for (let i = 1; i < 6; i++) {
      doc.line(tableX + colW * i, tableY, tableX + colW * i, tableY + 16);
    }

    y += 22;
  }

  // ── Report body ───────────────────────────────────────────────────────────
  const renderSectionHeader = (title: string) => {
    checkPage(14);
    doc.setFillColor(ar, ag, ab);
    doc.rect(ML, y, CW, 7, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text(title.toUpperCase(), ML + 3, y + 5);
    y += 9;
    doc.setTextColor(18, 32, 45);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
  };

  const renderBodyLines = (rawLines: string[]) => {
    for (const rawLine of rawLines) {
      if (!rawLine.trim()) { y += 2.5; continue; }
      checkPage(8);
      const headingMatch = rawLine.match(/^(#{1,4})\s+(.+)/);
      if (headingMatch) {
        checkPage(14);
        if (headingMatch[1].length <= 2) {
          renderSectionHeader(headingMatch[2]);
        } else {
          doc.setFont("helvetica", "bold");
          doc.setFontSize(10);
          doc.setTextColor(ar, ag, ab);
          doc.text(headingMatch[2], ML, y);
          y += 6;
          doc.setFont("helvetica", "normal");
          doc.setFontSize(9.5);
          doc.setTextColor(18, 32, 45);
        }
        continue;
      }
      const cleanLine = rawLine
        .replace(/\*\*(.+?)\*\*/g, "$1")
        .replace(/\*(.+?)\*/g, "$1")
        .replace(/`(.+?)`/g, "$1")
        .replace(/^[-*•]\s+/, "  • ");
      if (cleanLine.startsWith("  • ")) {
        doc.setTextColor(ar, ag, ab);
        doc.text("•", ML + 2, y);
        doc.setTextColor(18, 32, 45);
        const bulletLines = doc.splitTextToSize(cleanLine.slice(4), CW - 8) as string[];
        doc.text(bulletLines, ML + 7, y);
        y += bulletLines.length * 5.5 + 1;
      } else {
        const lines = doc.splitTextToSize(cleanLine, CW) as string[];
        doc.text(lines, ML, y);
        y += lines.length * 5.5 + 1;
      }
    }
  };

  if (bodyOverride) {
    renderBodyLines(bodyOverride.split("\n"));
  } else {
    for (const section of report.sections) {
      renderSectionHeader(section.heading);
      renderBodyLines(section.content.split("\n"));
      y += 4;
    }
  }

  // ── Footer on all pages ───────────────────────────────────────────────────
  const pageCount = doc.getNumberOfPages();
  for (let page = 1; page <= pageCount; page++) {
    doc.setPage(page);
    doc.setFillColor(ar, ag, ab);
    doc.rect(0, H - 10, W, 10, "F");
    doc.setTextColor(200, 220, 240);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.text(
      `EquityAI  ·  ${report.symbol}  ·  ${report.dataMode === "demo" ? "Demo Data" : "Live API"}  ·  Page ${page} of ${pageCount}`,
      W / 2, H - 3.5, { align: "center" }
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
  const [comparisonResult, setComparisonResult] = useState<CompareResultSnapshot | null>(null);
  const [comparisonResultLoading, setComparisonResultLoading] = useState(false);
  const [reportGenerating, setReportGenerating] = useState(false);
  const [aiReportBody, setAiReportBody] = useState<string | null>(null);

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
          setComparisonResult(null);
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
      setComparisonResult(null);
    }

    setLastSelectionStamp(searchSelection.stamp);
  }, [lastSelectionStamp, pushToast, searchSelection]);

  const [companyDetail, setCompanyDetail] = useState<AICompany | null>(null);
  const [companyQuote, setCompanyQuote] = useState<AIQuote | null>(null);
  const [quoteRefreshing, setQuoteRefreshing] = useState(false);
  const [companyRatios, setCompanyRatios] = useState<AIRatios | null>(null);
  const [companyFinancials, setCompanyFinancials] = useState<AIFinancials | null>(null);
  const [historicalPrices, setHistoricalPrices] = useState<AIHistoricalPrices | null>(null);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyTimeline, setCompanyTimeline] = useState<BackendTimelineEvent[]>([]);

  const loadCompanyById = useCallback(async (companyId: string) => {
    setCompanyLoading(true);
    setCompanyQuote(null);
    try {
      const [detail, ratios, financials] = await Promise.allSettled([
        fetchCompanyDetail(companyId),
        fetchCompanyRatios(companyId),
        fetchCompanyFinancials(companyId, 4),
      ]);
      let detailData: AICompany | null = null;
      if (detail.status === "fulfilled") {
        detailData = detail.value;
        setCompanyDetail(detailData);
      }
      if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
      if (financials.status === "fulfilled") setCompanyFinancials(financials.value);
      fetchCompanyQuote(companyId).then(setCompanyQuote).catch(() => {});
      fetchTimeline(undefined, companyId, 10).then(setCompanyTimeline).catch(() => {});
      fetchHistoricalPrices(companyId, 30).then(setHistoricalPrices).catch(() => {});

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
    setCompanyQuote(null);
    try {
      const results = await searchCompaniesDB(symbol, 5);
      if (results.length > 0) {
        const matched = results[0];
        const [detail, ratios, financials] = await Promise.allSettled([
          fetchCompanyDetail(matched.id),
          fetchCompanyRatios(matched.id),
          fetchCompanyFinancials(matched.id, 4),
        ]);
        let detailData: AICompany | null = null;
        if (detail.status === "fulfilled") {
          detailData = detail.value;
          setCompanyDetail(detailData);
        }
        if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
        if (financials.status === "fulfilled") setCompanyFinancials(financials.value);
        fetchCompanyQuote(matched.id).then(setCompanyQuote).catch(() => {});
        fetchTimeline(undefined, matched.id, 10).then(setCompanyTimeline).catch(() => {});
        fetchHistoricalPrices(matched.id, 30).then(setHistoricalPrices).catch(() => {});

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
        sector: companyDetail.sector ?? (companyLoading ? "Loading…" : "Enriching…"),
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

    if (comparisonResult) {
      const winnerTally: Record<string, number> = Object.fromEntries(
        comparisonCompanies.map((company) => [company.symbol, 0])
      );

      const pickWinnerSymbol = (winner: "A" | "B" | "Tie") => {
        if (winner === "A") return comparisonCompanies[0]?.symbol;
        if (winner === "B") return comparisonCompanies[1]?.symbol;
        return null;
      };

      const winners = [
        comparisonResult.comparison.growth,
        comparisonResult.comparison.profitability,
        comparisonResult.comparison.risk,
        comparisonResult.comparison.valuation,
      ];

      winners.forEach((winner) => {
        const symbol = pickWinnerSymbol(winner);
        if (symbol) {
          winnerTally[symbol] = (winnerTally[symbol] ?? 0) + 1;
        }
      });

      const strengths = comparisonCompanies.map((company) => {
        const wins = winnerTally[company.symbol] ?? 0;
        return {
          symbol: company.symbol,
          topTheme: "Category wins",
          score: wins * 25,
        };
      });

      const strongest = strengths.reduce((best, current) =>
        !best || current.score > best.score ? current : best
      );
      const weakest = strengths.reduce((worst, current) =>
        !worst || current.score < worst.score ? current : worst
      );

      const riskWinner = pickWinnerSymbol(comparisonResult.comparison.risk);
      const riskScores = comparisonCompanies.map((company) => ({
        symbol: company.symbol,
        score: company.symbol === riskWinner ? 18 : 42,
      }));

      const highestRisk = riskScores.reduce((best, current) =>
        !best || current.score > best.score ? current : best
      );
      const lowestRisk = riskScores.reduce((best, current) =>
        !best || current.score < best.score ? current : best
      );

      const divergence = [
        {
          theme: "Growth",
          spread: comparisonResult.comparison.growth === "Tie" ? 0 : 1,
        },
        {
          theme: "Profitability",
          spread: comparisonResult.comparison.profitability === "Tie" ? 0 : 1,
        },
        {
          theme: "Valuation",
          spread: comparisonResult.comparison.valuation === "Tie" ? 0 : 1,
        },
      ];

      return {
        strengths,
        strongest,
        weakest,
        highestRisk,
        lowestRisk,
        divergence,
      };
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
  }, [comparisonCompanies, comparisonResult, comparisonTimeline, reportScope]);

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

  const companyChartData = useMemo(() => {
    if (!companyFinancials || companyFinancials.periods.length === 0) return null;
    
    const sortedPeriods = [...companyFinancials.periods].sort(
      (a, b) => new Date(a.period_end).getTime() - new Date(b.period_end).getTime()
    );
    
    const labels = sortedPeriods.map(p => p.period_end);
    const revenueData = sortedPeriods.map(p => {
      const item = p.items.find(i => i.line_item === 'Revenue' || i.line_item === 'Sales');
      return item?.value ?? 0;
    });
    
    const profitData = sortedPeriods.map(p => {
      const item = p.items.find(i => i.line_item === 'Net Profit' || i.line_item === 'Net Profit+');
      return item?.value ?? 0;
    });

    return {
      labels,
      datasets: [
        {
          label: 'Revenue',
          data: revenueData,
          backgroundColor: 'rgba(53, 162, 235, 0.7)',
        },
        {
          label: 'Net Profit',
          data: profitData,
          backgroundColor: 'rgba(75, 192, 192, 0.7)',
        },
      ],
    };
  }, [companyFinancials]);

  const priceChartData = useMemo(() => {
    if (!historicalPrices || historicalPrices.prices.length === 0) return null;

    const prices = historicalPrices.prices;
    const labels = prices.map(p => {
      const d = new Date(p.date);
      return `${d.getDate()}/${d.getMonth() + 1}`;
    });
    const closeData = prices.map(p => p.close);
    const firstClose = closeData[0] ?? 0;
    const lastClose = closeData[closeData.length - 1] ?? 0;
    const isPositive = lastClose >= firstClose;

    return {
      labels,
      datasets: [
        {
          label: 'Close Price (₹)',
          data: closeData,
          borderColor: isPositive ? 'rgba(34, 197, 94, 1)' : 'rgba(239, 68, 68, 1)',
          backgroundColor: isPositive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 1.5,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
      ],
    };
  }, [historicalPrices]);

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
        const summaryIntro = comparisonResult
          ? comparisonResult.final_verdict
          : `${comparisonSummary.symbolsLabel} comparison indicates strongest momentum in ` +
            `${comparisonMetrics.strongest.symbol} (${comparisonMetrics.strongest.topTheme} ${comparisonMetrics.strongest.score}/100), ` +
            `while ${comparisonMetrics.weakest.symbol} trails on composite theme intensity (${comparisonMetrics.weakest.score}/100).`;

        sections.push({
          id: "summary",
          heading: "Executive Summary",
          content: summaryIntro,
        });
      }

      if (reportSections.includes("risks")) {
        const riskSpread = (comparisonMetrics.highestRisk.score - comparisonMetrics.lowestRisk.score).toFixed(1);
        const riskNarrative = comparisonResult?.detailed_comparison?.risk;
        sections.push({
          id: "risks",
          heading: "Risk Spread",
          content: riskNarrative
            ? `${riskNarrative}\nSpread marker: ${riskSpread}.`
            : `Highest modeled risk: ${comparisonMetrics.highestRisk.symbol} (${comparisonMetrics.highestRisk.score}).\n` +
              `Lowest modeled risk: ${comparisonMetrics.lowestRisk.symbol} (${comparisonMetrics.lowestRisk.score}).\n` +
              `Spread: ${riskSpread}. Monitor names with weaker average theme quality and clustered high-impact events.`,
        });
      }

      if (reportSections.includes("financials")) {
        const winnersText = comparisonResult
          ? `Company A summary: ${comparisonResult.companyA_summary}\nCompany B summary: ${comparisonResult.companyB_summary}`
          : [...comparisonCompanies]
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
        const divergenceText = comparisonResult?.insights?.length
          ? comparisonResult.insights.join("\n")
          : comparisonMetrics.divergence.length
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
    comparisonResult,
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

  const triggerReportGeneration = async () => {
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
      setReportGeneratedAt(new Date().toISOString());
      return;
    }

    const userId = localStorage.getItem("equityai-user-id") ?? "11111111-1111-1111-1111-111111111111";
    const ticker = nseOrBseTicker ?? companyData.symbol;
    const sectionsLabel = reportSections.join(", ");
    const prompt =
      `Generate a ${reportAudience}-level research report for ${companyData.name} (${ticker}). ` +
      `Include sections: ${sectionsLabel}. ` +
      "Focus on financials, key risks, investment thesis, and outlook. " +
      "Write in professional markdown with section headers and bullet points.";

    setReportGenerating(true);
    setAiReportBody(null);
    setReportGeneratedAt(new Date().toISOString());
    try {
      const res = await sendChatQuery({
        user_id: userId,
        query: prompt,
        expertise_level: reportAudience === "analyst" ? "advanced" : "beginner",
        ...(activeCompanyId ? { company_id: activeCompanyId } : {}),
      });
      setAiReportBody(res.response ?? "");
      pushToast("Report generated", "success");
    } catch {
      pushToast("AI report generation failed. Showing structured preview.", "warning");
    } finally {
      setReportGenerating(false);
    }
  };

  useEffect(() => {
    if (reportScope !== "comparison" || comparisonSymbols.length < 2 || dataMode !== "live") {
      return;
    }

    const userId =
      localStorage.getItem("equityai-user-id") ?? "11111111-1111-1111-1111-111111111111";

    let isCancelled = false;

    (async () => {
      setComparisonResultLoading(true);
      try {
        const result = await compareCompanies({
          user_id: userId,
          company_names: comparisonSymbols.slice(0, 2),
          expertise_level: "intermediate",
        });
        if (!isCancelled) {
          setComparisonResult({
            companyA_summary: result.companyA_summary,
            companyB_summary: result.companyB_summary,
            comparison: result.comparison,
            insights: result.insights,
            final_verdict: result.final_verdict,
            detailed_comparison: result.detailed_comparison,
          });
        }
      } catch {
        if (!isCancelled) {
          setComparisonResult(null);
        }
      } finally {
        if (!isCancelled) {
          setComparisonResultLoading(false);
        }
      }
    })();

    return () => {
      isCancelled = true;
    };
  }, [comparisonSymbols, dataMode, reportScope]);

  const exportReportAsText = () => {
    if (!generatedReport) return;

    const payload = [
      generatedReport.title,
      `Generated: ${new Date(generatedReport.generatedAt).toLocaleString()}`,
      generatedReport.audienceText,
      "",
      aiReportBody ?? generatedReport.body,
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
      const priceHistory = historicalPrices?.prices?.map(p => ({ date: p.date, close: p.close }));
      await exportReportAsPdf(generatedReport, aiReportBody, {
        lastPrice: companyQuote?.last_price ?? null,
        changePct: companyQuote?.change_pct ?? null,
        pe: companyRatioSnapshot.pe || undefined,
        pb: companyRatioSnapshot.pb || undefined,
        roe: companyRatioSnapshot.roe || undefined,
        debtToEquity: companyRatioSnapshot.debtToEquity || undefined,
        operatingMargin: companyRatioSnapshot.operatingMargin || undefined,
        beta: companyRatioSnapshot.beta || undefined,
        priceHistory: priceHistory?.length ? priceHistory : undefined,
      });
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
          <CompanySearchInput
            placeholder="Search company by name or ticker…"
            onSelect={(c) => {
              setActiveCompanyId(c.id);
              setActiveSymbol(c.ticker || c.name);
              setSymbolInput(c.ticker || c.name);
            }}
            className="w-72"
          />
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
            Ask Minerva
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
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div className="split-grid">
            <article className="feature-card">
              <div className="feature-head">
                <TrendingUp size={18} />
                <h3>Live Quote</h3>
                {activeCompanyId && (
                  <button
                    className="icon-btn"
                    title="Refresh quote"
                    style={{ marginLeft: "auto" }}
                    disabled={quoteRefreshing}
                    onClick={() => {
                      setQuoteRefreshing(true);
                      fetchCompanyQuote(activeCompanyId)
                        .then(setCompanyQuote)
                        .catch(() => {})
                        .finally(() => setQuoteRefreshing(false));
                    }}
                  >
                    <RefreshCw size={14} className={quoteRefreshing ? "spin" : ""} />
                  </button>
                )}
              </div>
              {companyQuote?.last_price ? (
                <>
                  <h2 style={{ margin: "8px 0 4px" }}>₹{Number(companyQuote.last_price).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</h2>
                  <div className="chip-row" style={{ margin: "4px 0 8px" }}>
                    {companyQuote.change_pct != null && (
                      <span className={`chip ${Number(companyQuote.change_pct) >= 0 ? "positive" : "negative"}`} style={{ fontWeight: 700 }}>
                        {Number(companyQuote.change_pct) >= 0 ? "+" : ""}{Number(companyQuote.change_pct).toFixed(2)}%
                      </span>
                    )}
                    {companyQuote.change != null && (
                      <span className={`chip ${Number(companyQuote.change) >= 0 ? "positive" : "negative"}`}>
                        {Number(companyQuote.change) >= 0 ? "+" : ""}₹{Number(companyQuote.change).toFixed(2)}
                      </span>
                    )}
                    {companyQuote.market_state && (
                      <span className="chip">{companyQuote.market_state}</span>
                    )}
                  </div>
                  {(companyQuote.fifty_two_week_high || companyQuote.fifty_two_week_low) && (
                    <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginBottom: 6 }}>
                      52W: ₹{Number(companyQuote.fifty_two_week_low ?? 0).toLocaleString("en-IN")} – ₹{Number(companyQuote.fifty_two_week_high ?? 0).toLocaleString("en-IN")}
                    </div>
                  )}
                  <small style={{ color: "var(--muted)" }}>
                    {companyQuote.source ?? "API"} · {companyQuote.fetched_at ? new Date(companyQuote.fetched_at).toLocaleTimeString() : ""}
                  </small>
                  <SourceBadges sources={companyQuote.data_sources} />
                </>
              ) : (
                <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  {companyLoading ? "Fetching quote…" : "No live quote available."}
                </p>
              )}
            </article>

            <article className="feature-card">
              <div className="feature-head">
                <Clock3 size={18} />
                <h3>Recent Events</h3>
              </div>
              {companyLoading ? (
                <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Fetching events…</p>
              ) : companyTimeline.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>No recent events found for this company.</p>
              ) : (
                <>
                  <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginBottom: 8 }}>{companyTimeline.length} event{companyTimeline.length !== 1 ? "s" : ""}</p>
                  {companyTimeline.slice(0, 5).map((ev) => (
                    <div key={ev.id} className="list-item">
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ margin: 0, fontSize: "0.84rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ev.title}</p>
                        {ev.metadata?.source_url ? (
                          <a href={ev.metadata.source_url as string} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.75rem", color: "var(--brand)" }}>
                            {(ev.metadata?.source as string) ?? "Source"} ↗
                          </a>
                        ) : (
                          <small style={{ color: "var(--muted)" }}>{(ev.metadata?.source as string) ?? ev.event_type}</small>
                        )}
                      </div>
                      <small style={{ flexShrink: 0, color: "var(--muted)" }}>{new Date(ev.timestamp).toLocaleDateString()}</small>
                    </div>
                  ))}
                </>
              )}
            </article>
          </div>

          {companyDetail?.gemini_extra && typeof companyDetail.gemini_extra === 'object' && !Array.isArray(companyDetail.gemini_extra) && (
            <div className="split-grid">
              <article className="feature-card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="feature-head" style={{ marginBottom: 0 }}>
                  <FileText size={18} />
                  <h3>Business Model & Operations</h3>
                </div>
                
                {Array.isArray(companyDetail.gemini_extra.business_model) && companyDetail.gemini_extra.business_model.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Core Business Model</h4>
                    <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.business_model.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  </div>
                )}
                
                {Array.isArray(companyDetail.gemini_extra.key_products) && companyDetail.gemini_extra.key_products.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Key Products & Services</h4>
                    <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.key_products.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  </div>
                )}

                {Array.isArray(companyDetail.gemini_extra.primary_geographies) && companyDetail.gemini_extra.primary_geographies.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Primary Geographies</h4>
                    <p style={{ margin: 0, fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.primary_geographies.join(", ")}
                    </p>
                  </div>
                )}
              </article>

              <article className="feature-card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div className="feature-head" style={{ marginBottom: 0 }}>
                  <BarChart3 size={18} />
                  <h3>Investment Thesis & Risks</h3>
                </div>
                
                {Array.isArray(companyDetail.gemini_extra.investment_highlights) && companyDetail.gemini_extra.investment_highlights.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--good)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Investment Highlights</h4>
                    <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.investment_highlights.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  </div>
                )}
                
                {Array.isArray(companyDetail.gemini_extra.major_risks) && companyDetail.gemini_extra.major_risks.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--bad)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Major Risks</h4>
                    <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.major_risks.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  </div>
                )}

                {Array.isArray(companyDetail.gemini_extra.key_competitors) && companyDetail.gemini_extra.key_competitors.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Key Competitors</h4>
                    <p style={{ margin: 0, fontSize: "0.85rem", lineHeight: 1.5, color: "var(--ink)" }}>
                      {companyDetail.gemini_extra.key_competitors.join(", ")}
                    </p>
                  </div>
                )}
              </article>
            </div>
          )}

          {companyDetail?.gemini_extra && typeof companyDetail.gemini_extra === 'object' && !Array.isArray(companyDetail.gemini_extra) && Array.isArray(companyDetail.gemini_extra.management_notes) && companyDetail.gemini_extra.management_notes.length > 0 && (
            <article className="feature-card">
              <div className="feature-head" style={{ marginBottom: "12px" }}>
                <FileText size={18} />
                <h3>Management Commentary & Notes</h3>
              </div>
              <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.85rem", lineHeight: 1.6, color: "var(--ink)" }}>
                {companyDetail.gemini_extra.management_notes.map((item, i) => <li key={i} style={{ marginBottom: "6px" }}>{item}</li>)}
              </ul>
            </article>
          )}
          {priceChartData && (
            <article className="feature-card">
              <div className="feature-head">
                <TrendingUp size={18} />
                <h3>Daily Stock Price — 30 Day Trend ({companyLabel})</h3>
              </div>
              <div style={{ height: '280px', marginTop: '16px' }}>
                <ChartLine
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                      mode: 'index' as const,
                      intersect: false,
                    },
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        callbacks: {
                          label: (ctx) => `₹${ctx.parsed.y.toLocaleString()}`,
                        },
                      },
                    },
                    scales: {
                      x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 10 },
                      },
                      y: {
                        ticks: {
                          callback: (val) => `₹${Number(val).toLocaleString()}`,
                        },
                      },
                    },
                  }}
                  data={priceChartData}
                />
              </div>
              {historicalPrices && (
                <div className="chip-row" style={{ marginTop: '8px' }}>
                  <span className="chip">Source: {historicalPrices.source ?? 'API'}</span>
                  <span className="chip">{historicalPrices.prices.length} days</span>
                  {historicalPrices.prices.length > 0 && (
                    <span className={`chip ${
                      historicalPrices.prices[historicalPrices.prices.length - 1].close >= historicalPrices.prices[0].close
                        ? 'positive' : 'warning'
                    }`}>
                      {(((historicalPrices.prices[historicalPrices.prices.length - 1].close - historicalPrices.prices[0].close) / historicalPrices.prices[0].close) * 100).toFixed(2)}% in period
                    </span>
                  )}
                </div>
              )}
            </article>
          )}
          {companyChartData && (
            <article className="feature-card">
              <div className="feature-head">
                <BarChart3 size={18} />
                <h3>Financial Performance ({companyLabel})</h3>
              </div>
              <div style={{ height: '300px', marginTop: '16px' }}>
                <Bar 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { position: 'top' as const },
                      title: { display: false }
                    }
                  }} 
                  data={companyChartData} 
                />
              </div>
            </article>
          )}
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
              Ask in Minerva
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
              <span className="chip">Source: {comparisonResult ? "Backend compare" : "Local heuristic"}</span>
            </div>
            {comparisonResultLoading ? <p>Loading backend comparison data...</p> : null}
            {comparisonResult ? <p>{comparisonResult.final_verdict}</p> : null}
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
          <button type="button" className="primary-btn" onClick={() => { void triggerReportGeneration(); }} disabled={reportGenerating}>
            {reportGenerating ? <><Loader2 size={14} className="spin" /> Generating…</> : "Generate Report"}
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

        {reportGenerating && (
          <div className="notice"><Loader2 size={16} className="spin" /> Generating AI report…</div>
        )}
        {!reportGenerating && generatedReport ? (
          <div className="report-preview">
            <div className="report-preview-header">
              <div className="report-preview-title-row">
                <FileText size={16} style={{ color: "var(--brand)", flexShrink: 0 }} />
                <h4 className="report-preview-title">{generatedReport.title}</h4>
              </div>
              <p className="report-preview-subtitle">{generatedReport.audienceText}</p>
              <div className="report-preview-chips">
                <span className="report-chip">
                  {generatedReport.scope === "comparison" ? "Comparison" : "Company"}
                </span>
                <span className="report-chip">
                  {generatedReport.audience === "retail" ? "Retail Brief" : "Analyst Dossier"}
                </span>
                <span className="report-chip report-chip--muted">
                  {new Date(generatedReport.generatedAt).toLocaleString("en-IN", {
                    day: "2-digit", month: "short", year: "numeric",
                    hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
            <div className="report-md">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {aiReportBody ?? generatedReport.body}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          !reportGenerating && (
            <p className="report-placeholder">
              Select sections and click Generate Report to build a company-specific brief.
            </p>
          )
        )}

      </article>
    </section>
  );
}
