import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  BranchPickerPrimitive,
  ActionBarPrimitive,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { type FC } from "react";
import { SendHorizontal, Square, ChevronLeft, ChevronRight, Copy, RefreshCw, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";

const MarkdownText: FC<{ text: string }> = () => (
  <MarkdownTextPrimitive />
);

export function Thread() {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex flex-1 flex-col items-center overflow-y-auto scroll-smooth px-4 pt-8">
        <ThreadWelcome />
        <ThreadPrimitive.Messages
          components={{
            UserMessage,
            AssistantMessage,
          }}
        />
        <ThreadScrollToBottom />
      </ThreadPrimitive.Viewport>
      <Composer />
    </ThreadPrimitive.Root>
  );
}

function ThreadWelcome() {
  return (
    <ThreadPrimitive.Empty>
      <div className="flex flex-col items-center justify-center gap-4 py-16 max-w-lg mx-auto text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-8 w-8"
          >
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <h2 className="text-2xl font-semibold text-foreground">
          Welcome to Iris
        </h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          Your AI-powered equity research assistant, powered by Sarvam AI.
          Ask me about financial filings, market sentiment, thematic analysis,
          or portfolio insights.
        </p>
        <div className="grid grid-cols-1 gap-2 w-full mt-4 sm:grid-cols-2">
          {[
            "Analyze the latest quarterly results for TCS",
            "What's the sentiment around renewable energy stocks?",
            "Explain the ripple effects of rising crude oil prices",
            "Summarize key highlights from Infosys concall",
          ].map((suggestion) => (
            <ThreadPrimitive.Suggestion
              key={suggestion}
              prompt={suggestion}
              autoSend
              className={cn(
                "cursor-pointer rounded-lg border border-border bg-accent/50 px-3 py-2 text-left text-xs text-muted-foreground",
                "transition-colors hover:bg-accent hover:text-foreground"
              )}
            >
              {suggestion}
            </ThreadPrimitive.Suggestion>
          ))}
        </div>
      </div>
    </ThreadPrimitive.Empty>
  );
}

function ThreadScrollToBottom() {
  return (
    <ThreadPrimitive.ScrollToBottom className="absolute bottom-28 right-4 rounded-full border border-border bg-background p-2 shadow-lg transition-opacity hover:bg-accent">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="h-4 w-4"
      >
        <path d="M12 5v14M5 12l7 7 7-7" />
      </svg>
    </ThreadPrimitive.ScrollToBottom>
  );
}

function Composer() {
  return (
    <ComposerPrimitive.Root className="mx-auto flex w-full max-w-2xl items-end gap-2 rounded-2xl border border-border bg-accent/30 p-3 mb-4 backdrop-blur-sm">
      <ComposerPrimitive.Input
        placeholder="Ask Iris anything about equity research..."
        rows={1}
        autoFocus
        className={cn(
          "flex-1 resize-none bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground",
          "max-h-40 min-h-9"
        )}
      />
      <ThreadPrimitive.If running>
        <ComposerPrimitive.Cancel className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive text-primary-foreground transition-colors hover:bg-destructive/80">
          <Square className="h-4 w-4" />
        </ComposerPrimitive.Cancel>
      </ThreadPrimitive.If>
      <ThreadPrimitive.If running={false}>
        <ComposerPrimitive.Send className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/80 disabled:opacity-30">
          <SendHorizontal className="h-4 w-4" />
        </ComposerPrimitive.Send>
      </ThreadPrimitive.If>
    </ComposerPrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="relative flex w-full max-w-2xl gap-3 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary">
        U
      </div>
      <div className="flex-1 space-y-1">
        <MessagePrimitive.Content
          components={{ Text: ({ text }) => <p className="text-sm leading-relaxed">{text}</p> }}
        />
        <UserActionBar />
      </div>
    </MessagePrimitive.Root>
  );
}

function UserActionBar() {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="flex gap-1 pt-1"
    >
      <ActionBarPrimitive.Edit className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground">
        <Pencil className="h-3 w-3" />
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="relative flex w-full max-w-2xl gap-3 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
        I
      </div>
      <div className="flex-1 space-y-1">
        <MessagePrimitive.Content
          components={{ Text: MarkdownText }}
        />
        <AssistantActionBar />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantActionBar() {
  return (
    <ActionBarPrimitive.Root
      autohide="not-last"
      className="flex items-center gap-1 pt-1"
    >
      <BranchPicker />
      <ActionBarPrimitive.Copy className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground">
        <Copy className="h-3 w-3" />
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground">
        <RefreshCw className="h-3 w-3" />
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
}

function BranchPicker() {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className="flex items-center gap-0.5 text-xs text-muted-foreground"
    >
      <BranchPickerPrimitive.Previous className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:text-foreground">
        <ChevronLeft className="h-3 w-3" />
      </BranchPickerPrimitive.Previous>
      <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      <BranchPickerPrimitive.Next className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:text-foreground">
        <ChevronRight className="h-3 w-3" />
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
}
