import { useEffect } from "react";

import {
  CHAT_ACTIVE_THREAD_STORAGE_KEY,
  CHAT_THREADS_STORAGE_KEY,
} from "../constants";
import type { ChatMessage, ChatThread } from "../types";
import { usePersistentState } from "./usePersistentState";

function createInitialThread(promptText?: string): ChatThread {
  const now = new Date().toISOString();
  const messageSeed = promptText?.trim();

  const messages: ChatMessage[] = [
    {
      id: `assistant-${Date.now()}-intro`,
      role: "assistant",
      text: "Iris is ready. Start with filings, risk, sentiment, or a compare query.",
      sources: ["Workspace context", "Timeline feed", "Discovery themes"],
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

function getInitialChatThreads(): ChatThread[] {
  const saved = window.localStorage.getItem(CHAT_THREADS_STORAGE_KEY);
  if (!saved) return [createInitialThread()];

  try {
    const parsed = JSON.parse(saved) as ChatThread[];
    if (!Array.isArray(parsed) || !parsed.length) return [createInitialThread()];
    return parsed.filter((thread) => thread.id && Array.isArray(thread.messages));
  } catch {
    return [createInitialThread()];
  }
}

export function useChatThreads() {
  const [chatThreads, setChatThreads] = usePersistentState<ChatThread[]>(
    CHAT_THREADS_STORAGE_KEY,
    getInitialChatThreads
  );
  const [activeChatThreadId, setActiveChatThreadId] = usePersistentState<string>(
    CHAT_ACTIVE_THREAD_STORAGE_KEY,
    () => ""
  );

  useEffect(() => {
    if (!chatThreads.length) {
      const thread = createInitialThread();
      setChatThreads([thread]);
      setActiveChatThreadId(thread.id);
      return;
    }

    if (activeChatThreadId && chatThreads.some((thread) => thread.id === activeChatThreadId)) {
      return;
    }

    const saved = window.localStorage.getItem(CHAT_ACTIVE_THREAD_STORAGE_KEY);
    if (saved && chatThreads.some((thread) => thread.id === saved)) {
      setActiveChatThreadId(saved);
      return;
    }

    setActiveChatThreadId(chatThreads[0].id);
  }, [activeChatThreadId, chatThreads, setActiveChatThreadId, setChatThreads]);

  return {
    chatThreads,
    setChatThreads,
    activeChatThreadId,
    setActiveChatThreadId,
    createInitialThread,
  };
}
