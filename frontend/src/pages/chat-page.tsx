import { Thread } from "@/components/assistant-ui/thread";

export function ChatPage() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            I
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">
              Iris Research Assistant
            </h1>
            <p className="text-xs text-muted-foreground">
              Powered by Sarvam AI
            </p>
          </div>
        </div>
        <span className="inline-flex items-center rounded-full bg-accent px-2.5 py-0.5 text-xs text-muted-foreground">
          Beta
        </span>
      </header>

      {/* Chat area */}
      <div className="relative flex-1 overflow-hidden">
        <Thread />
      </div>
    </div>
  );
}
