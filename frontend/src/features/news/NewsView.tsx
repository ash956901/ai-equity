import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Newspaper, Search, TrendingUp } from "lucide-react";

import {
  ApiError,
  fetchMarketHeadlines,
  fetchTickerSentiment,
  type NewsDataResponse,
  type SentimentFeedResponse,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";

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

  const [headlines, setHeadlines] = useState<NewsDataResponse>({});
  const [sentimentFeed, setSentimentFeed] = useState<SentimentFeedResponse | null>(null);

  const [loadingHeadlines, setLoadingHeadlines] = useState(true);
  const [loadingSentiment, setLoadingSentiment] = useState(true);

  const [headlinesError, setHeadlinesError] = useState<string | null>(null);
  const [sentimentError, setSentimentError] = useState<string | null>(null);

  const loadHeadlines = useCallback(async () => {
    setLoadingHeadlines(true);
    setHeadlinesError(null);

    if (props.dataMode === "demo") {
      setHeadlines({});
      setHeadlinesError(DEMO_BANNER_MSG);
      setLoadingHeadlines(false);
      return;
    }

    try {
      const data = await fetchMarketHeadlines(50, activeSymbol);
      setHeadlines(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setHeadlinesError("News API is not configured on backend yet (401).");
      } else {
        setHeadlinesError("Could not load market headlines.");
      }
    } finally {
      setLoadingHeadlines(false);
    }
  }, [activeSymbol, props.dataMode]);

  const loadSentiment = useCallback(
    async (symbol: string) => {
      setLoadingSentiment(true);
      setSentimentError(null);

      if (props.dataMode === "demo") {
        setSentimentFeed(null);
        setSentimentError(DEMO_BANNER_MSG);
        setLoadingSentiment(false);
        return;
      }

      try {
        const data = await fetchTickerSentiment(symbol, 24, 8);
        setSentimentFeed(data);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setSentimentError("Sentiment feed is unauthorized until backend keys are configured.");
        } else {
          setSentimentError(`Could not load sentiment for ${symbol}.`);
        }
        setSentimentFeed(null);
      } finally {
        setLoadingSentiment(false);
      }
    },
    [props.dataMode]
  );

  useEffect(() => {
    void loadHeadlines();
  }, [loadHeadlines]);

  useEffect(() => {
    void loadSentiment(activeSymbol);
  }, [activeSymbol, loadSentiment]);

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
    positive:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "positive").length ?? 0,
    neutral:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "neutral").length ?? 0,
    negative:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "negative").length ?? 0,
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="News & Sentiment Radar"
        subtitle="Monitor market narratives and detect sector-level shifts quickly."
        dataMode={props.dataMode}
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              const normalized = symbolInput.trim().toUpperCase();
              if (normalized) {
                setActiveSymbol(normalized);
              }
            }}
          >
            <Search size={14} />
            <input
              placeholder="Ticker symbol"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
            />
          </form>
        }
      />

      <div className="news-toolbar">
        <div className="chip-row">
          <span className="chip">Ticker: {activeSymbol}</span>
          <span className="chip">Headlines: {headlines.results?.length ?? 0}</span>
          <span className="chip">Sentiment: {sentimentFeed?.total_results ?? 0}</span>
        </div>
        <div className="chip-row">
          <button type="button" className="secondary-btn mini-btn" onClick={() => void loadHeadlines()}>
            Refresh Headlines
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => void loadSentiment(activeSymbol)}
          >
            Refresh Sentiment
          </button>
        </div>
      </div>

      {headlinesError ? <div className="notice warning">{headlinesError}</div> : null}
      {sentimentError ? <div className="notice warning">{sentimentError}</div> : null}

      <div className="split-grid">
        <article className="feature-card news-panel">
          <div className="feature-head">
            <Newspaper size={18} />
            <h3>Top Headlines</h3>
          </div>

          {loadingHeadlines ? (
            <p>Loading market headlines...</p>
          ) : (
            <div className="feed-list">
              {(headlines.results ?? []).slice(0, 8).map((article, index) => (
                <div key={`${article.article_id ?? article.link ?? index}`} className="feed-item-wrap">
                  <a href={article.link ?? "#"} target="_blank" rel="noreferrer" className="feed-item">
                    <p>{article.title ?? "Untitled headline"}</p>
                    <span>
                      {article.source_name ?? "Unknown source"}
                      {article.pubDate ? ` · ${article.pubDate}` : ""}
                    </span>
                  </a>
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() =>
                      props.addFavorite({
                        type: "headline",
                        symbol: activeSymbol,
                        title: article.title ?? "Untitled headline",
                        subtitle: article.source_name ?? "Unknown source",
                        url: article.link,
                      })
                    }
                    aria-label="Save headline to favorites"
                  >
                    {props.isFavorited({
                      type: "headline",
                      symbol: activeSymbol,
                      title: article.title ?? "Untitled headline",
                    }) ? (
                      <BookmarkCheck size={14} />
                    ) : (
                      <Bookmark size={14} />
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
                    <ArrowUpRight size={14} />
                  </button>
                </div>
              ))}
              {!(headlines.results ?? []).length ? <p>No headlines available for now.</p> : null}
            </div>
          )}
        </article>

        <article className="feature-card news-panel">
          <div className="feature-head">
            <TrendingUp size={18} />
            <h3>Sentiment Feed ({activeSymbol})</h3>
          </div>

          <div className="chip-row sentiment-row">
            <span className="chip positive">Positive: {sentimentCounts.positive}</span>
            <span className="chip">Neutral: {sentimentCounts.neutral}</span>
            <span className="chip negative">Negative: {sentimentCounts.negative}</span>
          </div>

          {loadingSentiment ? (
            <p>Loading sentiment feed...</p>
          ) : (
            <div className="feed-list">
              {(sentimentFeed?.articles ?? []).slice(0, 8).map((article, index) => (
                <div key={`${article.article_id ?? article.link ?? index}`} className="feed-item-wrap">
                  <a href={article.link ?? "#"} target="_blank" rel="noreferrer" className="feed-item">
                    <p>{article.title ?? "Untitled article"}</p>
                    <span>
                      {(article.sentiment ?? "unknown").toLowerCase()}
                      {article.source_name ? ` · ${article.source_name}` : ""}
                    </span>
                  </a>
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() =>
                      props.addFavorite({
                        type: "headline",
                        symbol: activeSymbol,
                        title: article.title ?? "Untitled article",
                        subtitle: `${article.sentiment ?? "unknown"} · ${article.source_name ?? "Unknown source"}`,
                        url: article.link,
                      })
                    }
                    aria-label="Save sentiment article to favorites"
                  >
                    {props.isFavorited({
                      type: "headline",
                      symbol: activeSymbol,
                      title: article.title ?? "Untitled article",
                    }) ? (
                      <BookmarkCheck size={14} />
                    ) : (
                      <Bookmark size={14} />
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
                    <ArrowUpRight size={14} />
                  </button>
                </div>
              ))}
              {!(sentimentFeed?.articles ?? []).length ? (
                <p>No sentiment articles available for this symbol.</p>
              ) : null}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
