import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Newspaper, TrendingUp } from "lucide-react";

import {
  ApiError,
  fetchNewsRadar,
  type EnrichedNewsItem,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { CompanySearchInput } from "../../shared/components/CompanySearchInput";

const DEMO_BANNER_MSG = "Demo mode — showing cached data. Switch to Live API for real-time results.";

interface SearchSelection {
  stamp: number;
  newsSymbol?: string;
}

interface FavoriteItem {
  type: "company" | "filing" | "headline";
  symbol?: string;
  title: string;
  subtitle?: string;
}

interface NewsViewProps {
  searchSelection: SearchSelection | null;
  dataMode: "live" | "demo";
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt"> & { url?: string }) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: "company") => void;
  setSearchSelection: (selection: { stamp: number; companySymbol: string; newsSymbol: string }) => void;
}

export function NewsView(props: NewsViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [symbolInput, setSymbolInput] = useState("RELIANCE");
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");

  const [articles, setArticles] = useState<EnrichedNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNews = useCallback(async (symbol: string, forceRefresh = false) => {
    setLoading(true);
    setError(null);

    if (props.dataMode === "demo") {
      setArticles([]);
      setError(DEMO_BANNER_MSG);
      setLoading(false);
      return;
    }

    try {
      const data = await fetchNewsRadar(50, symbol, "intermediate", forceRefresh);
      setArticles(data);
      if (data.length === 0) {
        setError(`No recent news indexed for ${symbol}. Click Refresh Data to fetch the latest articles.`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("News API is not configured on backend yet (401).");
      } else {
        setError(`Could not load news for ${symbol}. Check your network or try Refresh Data.`);
      }
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, [props.dataMode]);

  useEffect(() => {
    void loadNews(activeSymbol);
  }, [activeSymbol, loadNews]);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.newsSymbol) {
      const normalized = props.searchSelection.newsSymbol.toUpperCase();
      setSymbolInput(normalized);
      setActiveSymbol(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const sentimentCounts = {
    positive: articles.filter((item) => item.sentiment?.toLowerCase() === "positive").length,
    neutral: articles.filter((item) => item.sentiment?.toLowerCase() === "neutral").length,
    negative: articles.filter((item) => item.sentiment?.toLowerCase() === "negative").length,
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="News & Sentiment Radar"
        subtitle="Monitor market narratives, detect sector-level shifts, and track AI sentiment scoring."
        dataMode={props.dataMode}
        right={
          <CompanySearchInput
            placeholder="Search company for news…"
            onSelect={(c) => {
              const ticker = c.ticker || c.name;
              setSymbolInput(ticker);
              setActiveSymbol(ticker);
            }}
            className="w-64"
          />
        }
      />

      <div className="news-toolbar">
        <div className="chip-row">
          <span className="chip">Ticker: {activeSymbol}</span>
          <span className="chip">Articles: {articles.length}</span>
        </div>
        <div className="chip-row">
          <button type="button" className="secondary-btn mini-btn" onClick={() => void loadNews(activeSymbol, true)}>
            Refresh Data
          </button>
        </div>
      </div>

      {error ? (
        <div className={`notice ${articles.length === 0 ? "" : "warning"}`}>{error}</div>
      ) : null}

      <div className="split-grid" style={{ gridTemplateColumns: "1fr" }}>
        <article className="feature-card news-panel" style={{ width: "100%" }}>
          <div className="feature-head">
            <Newspaper size={18} />
            <h3>News & Sentiment Feed ({activeSymbol})</h3>
          </div>

          <div className="chip-row sentiment-row" style={{ marginBottom: "16px" }}>
            <span className="chip positive">Positive: {sentimentCounts.positive}</span>
            <span className="chip">Neutral: {sentimentCounts.neutral}</span>
            <span className="chip negative">Negative: {sentimentCounts.negative}</span>
          </div>

          {loading ? (
            <p>Loading market intelligence...</p>
          ) : (
            <div className="feed-list" style={{ gap: "12px" }}>
              {articles.map((article, index) => {
                const sentimentScore = (article.sentiment_confidence * 100).toFixed(0);
                const sentimentType = article.sentiment?.toLowerCase();
                const sentimentClass = sentimentType === "positive" ? "positive" : sentimentType === "negative" ? "negative" : "";
                
                return (
                  <div key={`${article.url ?? index}`} className="feed-item-wrap" style={{ gridTemplateColumns: "minmax(0, 1fr) auto" }}>
                    <a href={article.url ?? "#"} target="_blank" rel="noreferrer" className="feed-item" style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "14px" }}>
                      <div>
                        <p style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--ink)", lineHeight: 1.4 }}>
                          {article.title ?? "Untitled article"}
                        </p>
                        <p style={{ marginTop: "6px", fontSize: "0.82rem", color: "var(--muted)", lineHeight: 1.5 }}>
                          {article.summary}
                        </p>
                      </div>
                      <div className="chip-row" style={{ marginTop: "6px", gap: "6px" }}>
                        <span className={`chip ${sentimentClass}`} style={{ fontWeight: 600 }}>
                          {article.sentiment?.toUpperCase()} ({sentimentScore}%)
                        </span>
                        <span className="chip">{article.source}</span>
                        <span className="chip">{new Date(article.published_at).toLocaleString()}</span>
                        {article.categories?.map((cat) => (
                          <span key={cat} className="chip" style={{ background: "color-mix(in srgb, var(--brand) 10%, transparent)", borderColor: "color-mix(in srgb, var(--brand) 25%, transparent)", color: "var(--brand)" }}>
                            {cat}
                          </span>
                        ))}
                      </div>
                    </a>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", justifyContent: "flex-start", paddingTop: "4px" }}>
                      <button
                        type="button"
                        className="favorite-icon-btn"
                        onClick={() =>
                          props.addFavorite({
                            type: "headline",
                            symbol: activeSymbol,
                            title: article.title ?? "Untitled article",
                            subtitle: `${article.sentiment ?? "unknown"} · ${article.source ?? "Unknown source"}`,
                            url: article.url ?? undefined,
                          })
                        }
                        aria-label="Save sentiment article to favorites"
                      >
                        {props.isFavorited({
                          type: "headline",
                          symbol: activeSymbol,
                          title: article.title ?? "Untitled article",
                        }) ? (
                          <BookmarkCheck size={16} />
                        ) : (
                          <Bookmark size={16} />
                        )}
                      </button>
                      <button
                        type="button"
                        className="favorite-icon-btn"
                        onClick={() => {
                          props.setSearchSelection({
                            stamp: Date.now(),
                            companySymbol: activeSymbol,
                            newsSymbol: activeSymbol,
                          });
                          props.goToView("company");
                        }}
                        aria-label="Open company workspace"
                      >
                        <ArrowUpRight size={16} />
                      </button>
                    </div>
                  </div>
                );
              })}
              {!articles.length ? (
                <p>No market intelligence available for this symbol.</p>
              ) : null}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
