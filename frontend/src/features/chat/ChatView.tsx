import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type Dispatch,
  type SetStateAction,
} from "react";
import {
  ArrowUp,
  BookOpenText,
  Database,
  FileText,
  Loader2,
  Paperclip,
  Pencil,
  Pin,
  Plus,
  Search,
  Sparkles,
  Trash2,
  WandSparkles,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { listChatSessions, sendChatQuery, uploadDocument, type ChatQueryRequest } from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { ThinkingDropdown } from "./components/ThinkingDropdown";
import { ThinkingIndicator } from "./components/ThinkingIndicator";

type DataMode = "live" | "demo";

interface AgentEvent {
  timestamp: string;
  agent: string;
  event: string;
}

interface ToolCallEvent {
  timestamp: string;
  agent: string;
  tool: string;
  status: string;
}

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  sources?: string[];
  isThinking?: boolean;
  thinkingDurationSec?: number;
  executionPlan?: string[];
  agentEvents?: AgentEvent[];
  toolCalls?: ToolCallEvent[];
  attachedFile?: string;
}

interface ChatThread {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
  mode: "analyst" | "simple";
  messages: ChatMessage[];
  backendSessionId?: string;
}

interface SearchSelection {
  stamp: number;
  chatPrompt?: string;
}

interface ChatViewProps {
  searchSelection: SearchSelection | null;
  dataMode: DataMode;
  threads: ChatThread[];
  activeThreadId: string;
  setThreads: Dispatch<SetStateAction<ChatThread[]>>;
  setActiveThreadId: Dispatch<SetStateAction<string>>;
  createInitialThread: (promptText?: string) => ChatThread;
  demoBannerMessage: string;
}

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
}

export function ChatView(props: ChatViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [showSources, setShowSources] = useState(true);
  const [composerText, setComposerText] = useState("");
  const [threadQuery, setThreadQuery] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedUploadId, setAttachedUploadId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pendingPromptRef = useRef<string | null>(null);
  const isSendingRef = useRef(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const uid = getUserId();
    listChatSessions(uid).catch(() => {});
  }, []);

  const suggestions = [
    "What changed in RELIANCE latest filing?",
    "Summarize risk signals for my portfolio in simple terms.",
    "Compare IT services sentiment: TCS vs INFY.",
    "Explain why defense theme is heating up this week.",
  ];

  const activeThread = useMemo(
    () => props.threads.find((thread) => thread.id === props.activeThreadId) ?? props.threads[0] ?? null,
    [props.activeThreadId, props.threads]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeThread?.messages]);

  const sortedThreads = useMemo(() => {
    return [...props.threads].sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
  }, [props.threads]);

  const filteredThreads = useMemo(() => {
    const query = threadQuery.trim().toLowerCase();
    if (!query) return sortedThreads;

    return sortedThreads.filter((thread) => {
      const lastMessage = thread.messages[thread.messages.length - 1]?.text ?? "";
      return `${thread.title} ${lastMessage}`.toLowerCase().includes(query);
    });
  }, [sortedThreads, threadQuery]);

  const updateActiveThread = useCallback(
    (updater: (thread: ChatThread) => ChatThread) => {
      if (!activeThread) return;
      props.setThreads((current) =>
        current.map((thread) => (thread.id === activeThread.id ? updater(thread) : thread))
      );
    },
    [activeThread, props]
  );

  const createThread = useCallback(
    (initialPrompt?: string) => {
      const thread = props.createInitialThread(initialPrompt);
      props.setThreads((current) => [thread, ...current]);
      props.setActiveThreadId(thread.id);
      setThreadQuery("");
      return thread;
    },
    [props]
  );

  const handleFileSelect = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setAttachedFile(file);
      setIsUploading(true);

      try {
        const userId = localStorage.getItem("equityai-user-id") || crypto.randomUUID();
        localStorage.setItem("equityai-user-id", userId);

        const result = await uploadDocument(userId, file, activeThread?.backendSessionId);
        setAttachedUploadId(result.upload_id);
      } catch {
        setAttachedFile(null);
        setAttachedUploadId(null);
      } finally {
        setIsUploading(false);
        if (event.target) event.target.value = "";
      }
    },
    [activeThread]
  );

  const clearAttachment = useCallback(() => {
    setAttachedFile(null);
    setAttachedUploadId(null);
  }, []);

  const sendMessage = useCallback(async (overrideText?: string) => {
    const text = overrideText?.trim() || composerText.trim();
    if (!text || !activeThread) return;

    const now = new Date().toISOString();
    const currentFile = attachedFile;
    const currentUploadId = attachedUploadId;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      role: "user",
      text,
      attachedFile: currentFile?.name,
    };

    setComposerText("");
    clearAttachment();

    if (props.dataMode === "live") {
      const thinkingMessage: ChatMessage = {
        id: `assistant-thinking-${Date.now()}`,
        role: "assistant",
        text: "",
        isThinking: true,
      };

      props.setThreads((current) =>
        current.map((thread) => {
          if (thread.id !== activeThread.id) return thread;
          return {
            ...thread,
            title: thread.messages.length <= 1 ? text.slice(0, 44) : thread.title,
            updatedAt: now,
            messages: [...thread.messages, userMessage, thinkingMessage],
          };
        })
      );

      const startTime = performance.now();

      try {
        const userId = localStorage.getItem("equityai-user-id") || crypto.randomUUID();
        localStorage.setItem("equityai-user-id", userId);

        const expertiseLevel = activeThread.mode === "simple" ? "beginner" : "advanced";
        const chatReq: ChatQueryRequest = {
          user_id: userId,
          query: text,
          expertise_level: expertiseLevel,
          session_id: activeThread.backendSessionId,
        };
        if (currentUploadId) chatReq.upload_id = currentUploadId;
        const resp = await sendChatQuery(chatReq);

        const elapsedSec = Math.round((performance.now() - startTime) / 1000);

        const sources =
          resp.sources?.map((s: Record<string, unknown>) => String(s.title || s.source || JSON.stringify(s))) ??
          [];

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          role: "assistant",
          text: resp.response,
          sources: sources.length > 0 ? sources : undefined,
          thinkingDurationSec: elapsedSec,
          executionPlan: resp.execution_plan?.length ? resp.execution_plan : undefined,
          agentEvents: resp.agent_call_log?.length
            ? (resp.agent_call_log as unknown as AgentEvent[])
            : undefined,
          toolCalls: resp.tool_call_log?.length ? (resp.tool_call_log as unknown as ToolCallEvent[]) : undefined,
        };

        props.setThreads((current) =>
          current.map((thread) => {
            if (thread.id !== activeThread.id) return thread;
            const msgs = thread.messages.filter((m) => m.id !== thinkingMessage.id);
            return {
              ...thread,
              updatedAt: new Date().toISOString(),
              backendSessionId: resp.session_id,
              messages: [...msgs, assistantMessage],
            };
          })
        );
      } catch (err) {
        const errorMessage: ChatMessage = {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: `Error: ${err instanceof Error ? err.message : "Failed to get AI response"}. The AI backend may be unavailable.`,
        };

        props.setThreads((current) =>
          current.map((thread) => {
            if (thread.id !== activeThread.id) return thread;
            const msgs = thread.messages.filter((m) => m.id !== thinkingMessage.id);
            return {
              ...thread,
              updatedAt: new Date().toISOString(),
              messages: [...msgs, errorMessage],
            };
          })
        );
      }
    } else {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role: "assistant",
        text: props.demoBannerMessage + " Switch to Live API to get real AI-powered responses.",
      };

      props.setThreads((current) =>
        current.map((thread) => {
          if (thread.id !== activeThread.id) return thread;
          return {
            ...thread,
            title: thread.messages.length <= 1 ? text.slice(0, 44) : thread.title,
            updatedAt: now,
            messages: [...thread.messages, userMessage, assistantMessage],
          };
        })
      );
    }
  }, [activeThread, attachedFile, attachedUploadId, clearAttachment, composerText, props]);

  const renameThread = useCallback(
    (threadId: string) => {
      const target = props.threads.find((thread) => thread.id === threadId);
      if (!target) return;
      const next = window.prompt("Rename thread", target.title);
      if (!next || !next.trim()) return;

      props.setThreads((current) =>
        current.map((thread) =>
          thread.id === threadId
            ? { ...thread, title: next.trim().slice(0, 60), updatedAt: new Date().toISOString() }
            : thread
        )
      );
    },
    [props]
  );

  const deleteThread = useCallback(
    (threadId: string) => {
      if (props.threads.length <= 1) {
        const replacement = props.createInitialThread();
        props.setThreads([replacement]);
        props.setActiveThreadId(replacement.id);
        return;
      }

      const remaining = props.threads.filter((thread) => thread.id !== threadId);
      props.setThreads(remaining);
      if (props.activeThreadId === threadId) {
        props.setActiveThreadId(remaining[0].id);
      }
    },
    [props]
  );

  useEffect(() => {
    if (!activeThread) return;
    setComposerText((current) => (current ? current : ""));
  }, [activeThread]);

  // Handle incoming prompts from other views (e.g. "Ask Iris About This Event")
  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;
    setLastSelectionStamp(props.searchSelection.stamp);

    if (props.searchSelection.chatPrompt) {
      const prompt = props.searchSelection.chatPrompt;
      if (activeThread && activeThread.messages.length <= 1) {
        // Current thread is empty — queue the prompt to send
        pendingPromptRef.current = prompt;
        setComposerText(prompt);
      } else {
        // Create a fresh thread, then queue the prompt
        pendingPromptRef.current = prompt;
        const created = createThread();
        props.setActiveThreadId(created.id);
        setComposerText(prompt);
      }
    }
  }, [
    activeThread,
    createThread,
    lastSelectionStamp,
    props,
    props.searchSelection,
    props.setActiveThreadId,
  ]);

  // Consume pendingPromptRef once the active thread is ready
  useEffect(() => {
    if (!activeThread) return;
    if (!pendingPromptRef.current) return;
    if (isSendingRef.current) return;

    const prompt = pendingPromptRef.current;
    pendingPromptRef.current = null;
    isSendingRef.current = true;

    // Small delay so React state settles after thread creation
    const timer = setTimeout(() => {
      sendMessage(prompt).finally(() => {
        isSendingRef.current = false;
      });
    }, 50);
    return () => clearTimeout(timer);
  }, [activeThread, sendMessage]);

  if (!activeThread) return null;

  return (
    <section className="page-wrap chat-page-wrap">
      <PageHeader
        title="Minerva Research Copilot"
        subtitle="Persistent threads with mode-aware responses and reusable prompts."
        dataMode={props.dataMode}
        right={
          <div className="chat-controls">
            <button
              type="button"
              className={`mode-pill ${activeThread.mode === "analyst" ? "active" : ""}`}
              onClick={() =>
                updateActiveThread((thread) => ({
                  ...thread,
                  mode: "analyst",
                  updatedAt: new Date().toISOString(),
                }))
              }
            >
              <BookOpenText size={14} />
              Analyst Mode
            </button>
            <button
              type="button"
              className={`mode-pill ${activeThread.mode === "simple" ? "active" : ""}`}
              onClick={() =>
                updateActiveThread((thread) => ({
                  ...thread,
                  mode: "simple",
                  updatedAt: new Date().toISOString(),
                }))
              }
            >
              <WandSparkles size={14} />
              Explain Simply
            </button>
            <button
              type="button"
              className={`mode-pill ${showSources ? "active" : ""}`}
              onClick={() => setShowSources((current) => !current)}
            >
              Sources {showSources ? "On" : "Off"}
            </button>
          </div>
        }
      />

      <div className="chat-layout">
        <aside className="chat-threads-panel">
          <div className="chat-threads-head">
            <p className="results-title">Thread History</p>
            <button type="button" className="secondary-btn mini-btn" onClick={() => createThread()}>
              <Plus size={13} />
              New
            </button>
          </div>

          <div className="search-pill chat-thread-filter">
            <Search size={13} />
            <input
              placeholder="Filter threads"
              value={threadQuery}
              onChange={(event) => setThreadQuery(event.target.value)}
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
                        props.setThreads((current) =>
                          current.map((item) =>
                            item.id === thread.id
                              ? {
                                  ...item,
                                  pinned: !item.pinned,
                                  updatedAt: new Date().toISOString(),
                                }
                              : item
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
        </aside>

        <article className="chat-shell chat-main">
          {activeThread.messages.length <= 1 ? (
            <div className="chat-empty-state">
              <div className="chat-empty-logo">
                <Sparkles size={28} />
              </div>
              <h2>Minerva Research Copilot</h2>
              <p>Ask anything about Indian equities — filings, risk signals, sentiment, or portfolio strategy.</p>
              <div className="chat-empty-suggestions">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="chat-empty-suggestion-btn"
                    onClick={() => setComposerText(suggestion)}
                  >
                    {suggestion}
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
                      {message.attachedFile && (
                        <div className="chat-file-badge">
                          <Paperclip size={10} />
                          <span>{message.attachedFile}</span>
                        </div>
                      )}
                      <span>{message.text}</span>
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="chat-row chat-row--assistant">
                    <div className="chat-assistant-icon">
                      <Sparkles size={16} />
                    </div>
                    <div className="chat-assistant-body">
                      {message.isThinking ? (
                        <ThinkingIndicator />
                      ) : (
                        <>
                          <ThinkingDropdown message={message} />
                          <div className="message-text">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
                          </div>
                          {showSources && message.toolCalls?.length ? (
                            <div className="chat-sources-bar">
                              <span className="chat-sources-label">Sources</span>
                              <div className="chat-sources-list">
                                {message.toolCalls
                                  .filter((tc) => tc.status === "success")
                                  .map((tc, i) => (
                                    <span key={`src-tc-${tc.agent}-${tc.tool}-${i}`} className="chat-source-tag">
                                      <Database size={10} />
                                      <span>{tc.tool.replace(/_/g, " ")}</span>
                                    </span>
                                  ))}
                                {message.sources?.map((source, i) => (
                                  <span key={`src-ext-${message.id}-${i}`} className="chat-source-tag">
                                    <Database size={10} />
                                    <span>{source}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : showSources && message.sources?.length ? (
                            <div className="chat-sources-bar">
                              <span className="chat-sources-label">Sources</span>
                              <div className="chat-sources-list">
                                {message.sources.map((source, i) => (
                                  <span key={`src-${message.id}-${i}`} className="chat-source-tag">
                                    <Database size={10} />
                                    <span>{source}</span>
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

          {attachedFile && (
            <div className="chat-attachment-bar">
              <div className={`file-pill ${isUploading ? "uploading" : ""}`}>
                <FileText size={14} />
                <span>{attachedFile.name}</span>
                {isUploading ? (
                  <Loader2 size={14} className="spin" />
                ) : (
                  <button
                    type="button"
                    className="file-pill-remove"
                    onClick={clearAttachment}
                    aria-label="Remove file"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="chat-input-row">
            <input
              type="file"
              ref={fileInputRef}
              className="sr-only"
              accept=".pdf,.pptx,.ppt,.txt,.csv,.xlsx"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              className="chat-upload-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Attach document"
              disabled={isUploading}
            >
              <Paperclip size={16} />
            </button>
            <input
              placeholder={attachedFile ? "Ask about this document..." : "Ask Minerva anything about equities..."}
              value={composerText}
              onChange={(event) => setComposerText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  sendMessage();
                }
              }}
            />
            <button
              type="button"
              className="chat-send-btn"
              onClick={sendMessage}
              disabled={isUploading || !composerText.trim()}
              aria-label="Send message"
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}
