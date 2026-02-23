import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const SARVAM_API_KEY =
  import.meta.env.VITE_SARVAM_API_KEY ?? "";

const SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions";

/**
 * ChatModelAdapter that connects to Sarvam AI's chat completions API (sarvam-m model).
 * Falls back to a friendly message when the API key is missing or the API is unreachable.
 */
const SarvamModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    // Extract text from assistant-ui message format
    const formattedMessages = messages.map((m) => ({
      role: m.role,
      content: m.content
        .filter((c) => c.type === "text")
        .map((c) => {
          if (c.type === "text") return c.text;
          return "";
        })
        .join("\n"),
    }));

    // Prepend system prompt for Iris persona
    const systemMessage = {
      role: "system" as const,
      content:
        "You are Iris, an AI-powered equity research assistant for Indian markets. " +
        "You help retail investors understand financial filings, quarterly results, " +
        "market sentiment, and thematic ripple effects across sectors. " +
        "Be concise, data-driven, and always ground your answers in facts. " +
        "If you don't have enough context, say so honestly.",
    };

    const apiMessages = [systemMessage, ...formattedMessages];

    try {
      if (!SARVAM_API_KEY) {
        throw new Error("SARVAM_API_KEY_MISSING");
      }

      const response = await fetch(SARVAM_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "api-subscription-key": SARVAM_API_KEY,
        },
        body: JSON.stringify({
          model: "sarvam-m",
          messages: apiMessages,
          temperature: 0.2,
          top_p: 1,
          max_tokens: 2048,
          stream: false,
        }),
        signal: abortSignal,
      });

      if (!response.ok) {
        const errorBody = await response.text().catch(() => "");
        throw new Error(`Sarvam API error ${response.status}: ${errorBody || response.statusText}`);
      }

      const data = await response.json();
      const text =
        data.choices?.[0]?.message?.content ??
        "I couldn't generate a response. Please try again.";

      // Simulate streaming for smoother UX
      let streamed = "";
      const words = text.split(" ");
      for (let i = 0; i < words.length; i++) {
        streamed += (i > 0 ? " " : "") + words[i];
        yield { content: [{ type: "text" as const, text: streamed }] };
        await new Promise((r) => setTimeout(r, 15));
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      const lastUserMessage = [...messages]
        .reverse()
        .find((m) => m.role === "user");
      const userText =
        lastUserMessage?.content
          .filter((c) => c.type === "text")
          .map((c) => {
            if (c.type === "text") return c.text;
            return "";
          })
          .join("\n") ?? "";

      const isKeyMissing =
        error instanceof Error && error.message === "SARVAM_API_KEY_MISSING";

      const fallbackResponse = isKeyMissing
        ? `🔑 **Sarvam API key not configured**\n\n` +
          `To connect Iris to the Sarvam AI backend, add your API key to \`.env\`:\n\n` +
          `\`\`\`\nVITE_SARVAM_API_KEY=your_api_key_here\n\`\`\`\n\n` +
          `Get your key at [dashboard.sarvam.ai](https://dashboard.sarvam.ai).\n\n` +
          `> **Your message:** ${userText}`
        : `🔌 **Could not reach Sarvam AI**\n\n` +
          `${error instanceof Error ? error.message : "Unknown error"}\n\n` +
          `> **Your message:** ${userText}`;

      let streamed = "";
      for (const char of fallbackResponse) {
        streamed += char;
        yield { content: [{ type: "text" as const, text: streamed }] };
        await new Promise((r) => setTimeout(r, 5));
      }
    }
  },
};

interface RuntimeProviderProps {
  children: ReactNode;
}

export function RuntimeProvider({ children }: RuntimeProviderProps) {
  const runtime = useLocalRuntime(SarvamModelAdapter, {
    initialMessages: [],
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
