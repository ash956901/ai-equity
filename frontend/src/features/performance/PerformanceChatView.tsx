import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import {
  ArrowUp,
  Database,
  Loader2,
  Pencil,
  Pin,
  Plus,
  Search,
  TrendingDown,
  TrendingUp,
  Trash2,
  Trophy,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { streamChatQuery, type ChatQueryRequest } from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { ThinkingIndicator } from "../chat/components/ThinkingIndicator";
import { ThinkingDropdown } from "../chat/components/ThinkingDropdown";
import type { ChatThread, ChatMessage } from "../../app/types";

type ExpertiseLevel = "beginner" | "intermediate" | "advanced";
type DataMode = "live" | "demo";

interface PortfolioSnapshot {
  totalReturnPct: number | null;
  winnersCount: number;
  losersCount: number;
  totalValue: number | null;
}

interface PerformanceChatViewProps {
  dataMode: DataMode;
  pushToast: (message: string, tone?: "info" | "success" | "warning") => void;
  threads: ChatThread[];
  activeThreadId: string;
  setThreads: Dispatch<SetStateAction<ChatThread[]>>;
  setActiveThreadId: Dispatch<SetStateAction<string>>;
  createInitialThread: () => ChatThread;
}

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
}

const SUGGESTED_PROMPTS = [
  "What are my top 3 mistakes this month?",
  "Which holding is dragging my portfolio returns?",
  "Should I continue holding my current top position?",
  "Show me my best performing sector allocation.",
  "What is my portfolio's risk-adjusted return?",
  "Compare my returns against Nifty50 this month.",
];

function MarkdownWithBadges({ text }: { text: string }) {
  const parts = text.split(/(\b(?:BUY|SELL|HOLD)\b)/g);
  return (
    <div className="message-text">
      {parts.map((part, i) => {
        if (part === "BUY")
          return <span key={i} className="performance-badge performance-badge--buy">BUY</span>;
        if (part === "SELL")
          return <span key={i} className="performance-badge performance-badge--sell">SELL</span>;
        if (part === "HOLD")
          return <span key={i} className="performance-badge performance-badge--hold">HOLD</span>;
        return <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{part}</ReactMarkdown>;
      })}
    </div>
  );
}

export function PerformanceChatView(props: PerformanceChatViewProps) {
  const [expertiseLevel, setExpertiseLevel] = useState<ExpertiseLevel>("intermediate");
  const [composerText, setComposerText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [threadQuery, setThreadQuery] = useState("");
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot>({
    totalReturnPct: null,
    winnersCount: 0,
    losersCount: 0,
    totalValue: null,
  });
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const activeThread = useMemo(
    () => props.threads.find((t) => t.id === props.activeThreadId) ?? props.threads[0] ?? null,
    [props.activeThreadId, props.threads]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeThread?.messages]);

  useEffect(() => {
    const userId = getUserId();
    setSnapshotLoading(true);
    fetch(`${import.meta.env.VITE_AI_BACKEND_URL || "http://localhost:8001"}/portfolios/metrics?user_id=${userId}`)
      .then((r) => r.json())
      .then((data: { total_value_inr?: number; holdings?: { return_pct?: number }[] }) => {
        if (data?.holdings) {
          const winners = data.holdings.filter((h) => (h.return_pct ?? 0) > 0).length;
          const losers = data.holdings.filter((h) => (h.return_pct ?? 0) < 0).length;
          const avgReturn =
            data.holdings.length > 0
              ? data.holdings.reduce((s, h) => s + (h.return_pct ?? 0), 0) / data.holdings.length
              : null;
          setSnapshot({
            totalReturnPct: avgReturn,
            winnersCount: winners,
            losersCount: losers,
            totalValue: data.total_value_inr ?? null,
          });
        }
      })
      .catch(() => {})
      .finally(() => setSnapshotLoading(false));
  }, []);

  const sortedThreads = useMemo(() => {
    return [...props.threads].sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
  }, [props.threads]);

  const filteredThreads = useMemo(() => {
    const q = threadQuery.trim().toLowerCase();
    if (!q) return sortedThreads;
    return sortedThreads.filter((t) => {
      const last = t.messages[t.messages.length - 1]?.text ?? "";
      return `${t.title} ${last}`.toLowerCase().includes(q);
    });
  }, [sortedThreads, threadQuery]);

  const createThread = useCallback(() => {
    const thread = props.createInitialThread();
    props.setThreads((cur) => [thread, ...cur]);
    props.setActiveThreadId(thread.id);
    setThreadQuery("");
  }, [props]);

  const deleteThread = useCallback(
    (id: string) => {
      props.setThreads((cur) => {
        const next = cur.filter((t) => t.id !== id);
        if (!next.length) {
          const fresh = props.createInitialThread();
          props.setActiveThreadId(fresh.id);
          return [fresh];
        }
        if (id === props.activeThreadId) {
          props.setActiveThreadId(next[0].id);
        }
        return next;
      });
    },
    [props]
  );

  const renameThread = useCallback(
    (id: string) => {
      const thread = props.threads.find((t) => t.id === id);
      if (!thread) return;
      const name = window.prompt("Rename thread:", thread.title);
      if (!name?.trim()) return;
      props.setThreads((cur) =>
        cur.map((t) => (t.id === id ? { ...t, title: name.trim(), updatedAt: new Date().toISOString() } : t))
      );
    },
    [props]
  );

  const sendMessage = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText ?? composerText).trim();
      if (!text || isLoading || !activeThread) return;

      const userId = getUserId();
      const now = new Date().toISOString();

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        text,
      };
      const thinkingMsg: ChatMessage = {
        id: `thinking-${Date.now()}`,
        role: "assistant",
        text: "",
        isThinking: true,
      };

      setComposerText("");
      props.setThreads((cur) =>
        cur.map((t) =>
          t.id !== activeThread.id
            ? t
            : {
                ...t,
                title: t.messages.length <= 1 ? text.slice(0, 44) : t.title,
                updatedAt: now,
                messages: [...t.messages, userMsg, thinkingMsg],
              }
        )
      );
      setIsLoading(true);

      if (props.dataMode !== "live") {
        setTimeout(() => {
          props.setThreads((cur) =>
            cur.map((t) =>
              t.id !== activeThread.id
                ? t
                : {
                    ...t,
                    messages: t.messages.map((m) =>
                      m.id === thinkingMsg.id
                        ? { ...m, isThinking: false, text: "Switch to Live API mode to get real AI-powered portfolio analysis." }
                        : m
                    ),
                  }
            )
          );
          setIsLoading(false);
        }, 600);
        return;
      }

      const portfolioContext =
        snapshot.totalReturnPct !== null
          ? ` My portfolio average return is ${snapshot.totalReturnPct.toFixed(2)}%. I have ${snapshot.winnersCount} winners and ${snapshot.losersCount} losers.`
          : "";
      const enrichedQuery = `[Performance Analysis] ${text}${portfolioContext}`;
      const startTime = performance.now();

      try {
        const req: ChatQueryRequest = {
          user_id: userId,
          query: enrichedQuery,
          expertise_level: expertiseLevel,
          session_id: activeThread.backendSessionId,
        };
        let acc = "";
        const patch = (partial: Partial<ChatMessage>) =>
          props.setThreads((cur) =>
            cur.map((t) =>
              t.id !== activeThread.id
                ? t
                : {
                    ...t,
                    updatedAt: new Date().toISOString(),
                    messages: t.messages.map((m) => (m.id === thinkingMsg.id ? { ...m, ...partial } : m)),
                  }
            )
          );
        await streamChatQuery(req, {
          onToken: (tok) => {
            acc += tok;
            patch({ text: acc, isThinking: false });
          },
          onDone: (data) => {
            patch({ isThinking: false, thinkingDurationSec: Math.round((performance.now() - startTime) / 1000) });
            if (data.session_id) {
              props.setThreads((cur) =>
                cur.map((t) => (t.id === activeThread.id ? { ...t, backendSessionId: data.session_id } : t))
              );
            }
          },
          onError: (d) => patch({ isThinking: false, text: `Error: ${d}` }),
        });
      } catch (err) {
        props.pushToast("Performance analysis failed — check backend connection.", "warning");
        props.setThreads((cur) =>
          cur.map((t) =>
            t.id !== activeThread.id
              ? t
              : {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === thinkingMsg.id
                      ? { ...m, isThinking: false, text: `Error: ${err instanceof Error ? err.message : "Failed"}` }
                      : m
                  ),
                }
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [composerText, isLoading, activeThread, props, snapshot, expertiseLevel]
  );

  const returnColor =
    snapshot.totalReturnPct === null
      ? "var(--text-muted)"
      : snapshot.totalReturnPct >= 0
        ? "var(--color-positive)"
        : "var(--color-negative)";

  if (!activeThread) return null;

  return (
    <section className="page-wrap chat-page-wrap">
      <PageHeader
        title="Performance Coach"
        subtitle="AI-powered portfolio analysis with buy/sell/hold recommendations and learning insights."
        dataMode={props.dataMode}
        right={
          <div className="chat-controls">
            {(["beginner", "intermediate", "advanced"] as ExpertiseLevel[]).map((level) => (
              <button
                key={level}
                type="button"
                className={`mode-pill ${expertiseLevel === level ? "active" : ""}`}
                onClick={() => setExpertiseLevel(level)}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        }
      />

      {/* Portfolio snapshot banner */}
      <div className="perf-banner">
        {snapshotLoading ? (
          <div className="perf-banner__loading">
            <Loader2 size={14} className="spin" />
            <span>Loading portfolio snapshot…</span>
          </div>
        ) : (
          <>
            <div className="perf-banner__metric">
              <Trophy size={16} />
              <span className="perf-banner__label">Avg Return</span>
              <span className="perf-banner__value" style={{ color: returnColor }}>
                {snapshot.totalReturnPct !== null
                  ? `${snapshot.totalReturnPct >= 0 ? "+" : ""}${snapshot.totalReturnPct.toFixed(2)}%`
                  : "—"}
              </span>
            </div>
            <div className="perf-banner__sep" />
            <div className="perf-banner__metric">
              <TrendingUp size={16} />
              <span className="perf-banner__label">Winners</span>
              <span className="perf-banner__value" style={{ color: "var(--color-positive)" }}>
                {snapshot.winnersCount}
              </span>
            </div>
            <div className="perf-banner__sep" />
            <div className="perf-banner__metric">
              <TrendingDown size={16} />
              <span className="perf-banner__label">Losers</span>
              <span className="perf-banner__value" style={{ color: "var(--color-negative)" }}>
                {snapshot.losersCount}
              </span>
            </div>
            {snapshot.totalValue !== null && (
              <>
                <div className="perf-banner__sep" />
                <div className="perf-banner__metric">
                  <span className="perf-banner__label">Portfolio Value</span>
                  <span className="perf-banner__value">₹{(snapshot.totalValue / 100000).toFixed(2)}L</span>
                </div>
              </>
            )}
            <div className="perf-banner__sep" />
            <div className="perf-banner__metric">
              <span className="perf-banner__label">vs Nifty50</span>
              <span className="perf-banner__value perf-banner__value--muted">—</span>
            </div>
          </>
        )}
      </div>

      <div className="chat-layout">
        {/* Thread sidebar */}
        <aside className="chat-threads-panel">
          <div className="chat-threads-head">
            <p className="results-title">Thread History</p>
            <button type="button" className="secondary-btn mini-btn" onClick={createThread}>
              <Plus size={13} />
              New
            </button>
          </div>

          <div className="search-pill chat-thread-filter">
            <Search size={13} />
            <input
              placeholder="Filter threads"
              value={threadQuery}
              onChange={(e) => setThreadQuery(e.target.value)}
            />
          </div>

          <div className="chat-thread-list">
            {filteredThreads.length ? (
              filteredThreads.map((thread) => (
                <div
                  key={thread.id}
                  className={`chat-thread-item ${thread.id === activeThread.id ? "active" : ""}`}
                >
                  <button
                    type="button"
                    className="chat-thread-main"
                    onClick={() => props.setActiveThreadId(thread.id)}
                  >
                    <p>{thread.title || "Untitled thread"}</p>
                    <span>
                      {thread.messages.length} msgs · {new Date(thread.updatedAt).toLocaleDateString()}
                    </span>
                  </button>
                  <div className="chat-thread-actions">
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() =>
                        props.setThreads((cur) =>
                          cur.map((t) =>
                            t.id === thread.id ? { ...t, pinned: !t.pinned, updatedAt: new Date().toISOString() } : t
                          )
                        )
                      }
                      aria-label="Pin thread"
                    >
                      <Pin size={13} />
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() => renameThread(thread.id)}
                      aria-label="Rename thread"
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() => deleteThread(thread.id)}
                      aria-label="Delete thread"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p className="chat-thread-empty">No threads match this filter.</p>
            )}
          </div>

          <div style={{ marginTop: "auto", padding: "12px 16px", borderTop: "1px solid var(--border-subtle)" }}>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Performance Coach uses your live portfolio data and trade history to give personalised coaching.
            </p>
          </div>
        </aside>

        {/* Chat area */}
        <article className="chat-shell chat-main">
          {activeThread.messages.length <= 1 ? (
            <div className="chat-empty-state">
              <div className="chat-empty-logo">
                <Trophy size={28} />
              </div>
              <h2>Performance Coach</h2>
              <p>
                Get personalised insights about your portfolio — strengths, mistakes, sector exposure,
                and AI-driven BUY / HOLD / SELL signals.
              </p>
              <div className="chat-empty-suggestions">
                {SUGGESTED_PROMPTS.slice(0, 4).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="chat-empty-suggestion-btn"
                    onClick={() => sendMessage(s)}
                    disabled={isLoading}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-messages-area">
              {activeThread.messages.map((message) =>
                message.role === "user" ? (
                  <div key={message.id} className="chat-row chat-row--user">
                    <div className="chat-bubble-user">
                      <span>{message.text}</span>
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="chat-row chat-row--assistant">
                    <div className="chat-assistant-icon">
                      <Trophy size={16} />
                    </div>
                    <div className="chat-assistant-body">
                      {message.isThinking ? (
                        <ThinkingIndicator />
                      ) : (
                        <>
                          <ThinkingDropdown message={message} />
                          <MarkdownWithBadges text={message.text} />
                          {message.toolCalls?.length ? (
                            <div className="chat-sources-bar">
                              <span className="chat-sources-label">Sources</span>
                              <div className="chat-sources-list">
                                {message.toolCalls
                                  .filter((tc) => tc.status === "success")
                                  .map((tc, i) => (
                                    <span key={i} className="chat-source-tag">
                                      <Database size={10} />
                                      <span>{tc.tool.replace(/_/g, " ")}</span>
                                    </span>
                                  ))}
                              </div>
                            </div>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>
                )
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          <div className="chat-input-row">
            <input
              placeholder="Ask about your portfolio performance, holdings, or strategy..."
              value={composerText}
              onChange={(e) => setComposerText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void sendMessage();
                }
              }}
              disabled={isLoading}
            />
            <button
              type="button"
              className="chat-send-btn"
              onClick={() => void sendMessage()}
              disabled={isLoading || !composerText.trim()}
              aria-label="Send"
            >
              {isLoading ? <Loader2 size={16} className="spin" /> : <ArrowUp size={18} />}
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}
