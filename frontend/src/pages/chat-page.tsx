import { Thread } from "@/components/assistant-ui/thread";
import { Sparkles } from "lucide-react";

export function ChatPage() {
  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-3 shrink-0 bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-linear-to-br from-primary to-indigo-400 shadow-sm shadow-primary/20">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">
              Iris Research Assistant
            </h1>
            <p className="text-[11px] text-muted-foreground">
              Powered by Sarvam AI · sarvam-m
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-[11px] font-medium text-success ring-1 ring-success/20">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
            Online
          </span>
        </div>
      </header>

      {/* Chat area */}
      <div className="relative flex-1 overflow-hidden">
        <Thread />
      </div>
    </div>
  );
}
