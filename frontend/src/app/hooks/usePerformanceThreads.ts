import { useEffect } from "react";

import {
  PERFORMANCE_ACTIVE_THREAD_STORAGE_KEY,
  PERFORMANCE_THREADS_STORAGE_KEY,
} from "../constants";
import type { ChatMessage, ChatThread } from "../types";
import { usePersistentState } from "./usePersistentState";

function createInitialThread(): ChatThread {
  const now = new Date().toISOString();
  const messages: ChatMessage[] = [
    {
      id: `assistant-${Date.now()}-intro`,
      role: "assistant",
      text: "Minerva Performance Coach is ready. Ask about your returns, mistakes, risk, or get hold/sell recommendations.",
      sources: ["Portfolio holdings", "Live prices", "Trade history"],
    },
  ];
  return {
    id: `thread-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title: "New thread",
    pinned: false,
    createdAt: now,
    updatedAt: now,
    mode: "analyst",
    messages,
  };
}

function getInitialPerformanceThreads(): ChatThread[] {
  const saved = window.localStorage.getItem(PERFORMANCE_THREADS_STORAGE_KEY);
  if (!saved) return [createInitialThread()];
  try {
    const parsed = JSON.parse(saved) as ChatThread[];
    if (!Array.isArray(parsed) || !parsed.length) return [createInitialThread()];
    return parsed.filter((t) => t.id && Array.isArray(t.messages));
  } catch {
    return [createInitialThread()];
  }
}

export function usePerformanceThreads() {
  const [performanceThreads, setPerformanceThreads] = usePersistentState<ChatThread[]>(
    PERFORMANCE_THREADS_STORAGE_KEY,
    getInitialPerformanceThreads
  );
  const [activePerformanceThreadId, setActivePerformanceThreadId] = usePersistentState<string>(
    PERFORMANCE_ACTIVE_THREAD_STORAGE_KEY,
    () => ""
  );

  useEffect(() => {
    if (!performanceThreads.length) {
      const thread = createInitialThread();
      setPerformanceThreads([thread]);
      setActivePerformanceThreadId(thread.id);
      return;
    }
    if (
      activePerformanceThreadId &&
      performanceThreads.some((t) => t.id === activePerformanceThreadId)
    ) {
      return;
    }
    const saved = window.localStorage.getItem(PERFORMANCE_ACTIVE_THREAD_STORAGE_KEY);
    if (saved && performanceThreads.some((t) => t.id === saved)) {
      setActivePerformanceThreadId(saved);
      return;
    }
    setActivePerformanceThreadId(performanceThreads[0].id);
  }, [activePerformanceThreadId, performanceThreads, setActivePerformanceThreadId, setPerformanceThreads]);

  return {
    performanceThreads,
    setPerformanceThreads,
    activePerformanceThreadId,
    setActivePerformanceThreadId,
    createInitialThread,
  };
}
