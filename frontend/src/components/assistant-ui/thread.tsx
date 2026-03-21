import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  BranchPickerPrimitive,
  ActionBarPrimitive,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { type FC } from "react";
import {
  SendHorizontal,
  Square,
  ChevronLeft,
  ChevronRight,
  Copy,
  RefreshCw,
  Pencil,
  ArrowDown,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const MarkdownText: FC<{ text: string }> = () => (
  <MarkdownTextPrimitive />
);

export function Thread() {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex flex-1 flex-col items-center overflow-y-auto scroll-smooth px-4 pt-8 pb-4">
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
      <div className="flex flex-col items-center justify-center gap-6 py-20 max-w-md mx-auto text-center">
        <div className="relative">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-linear-to-br from-primary/20 to-indigo-500/10 text-primary ring-1 ring-primary/20">
            <Sparkles className="h-7 w-7" />
          </div>
          <div className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full bg-success ring-2 ring-background" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">
            Hi, I'm Iris
          </h2>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-sm">
            Your AI equity research assistant. Ask me about financial filings,
            market sentiment, or thematic analysis.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 w-full mt-2 sm:grid-cols-2">
          {[
            "Analyze TCS quarterly results",
            "Renewable energy stock sentiment",
            "Ripple effects of rising crude oil",
            "Infosys concall key highlights",
          ].map((suggestion) => (
            <ThreadPrimitive.Suggestion
              key={suggestion}
              prompt={suggestion}
              autoSend
              className={cn(
                "cursor-pointer rounded-xl border border-border/60 bg-card px-4 py-3 text-left text-[13px] text-muted-foreground",
                "transition-all duration-150 hover:border-primary/30 hover:bg-primary/5 hover:text-foreground"
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
    <ThreadPrimitive.ScrollToBottom className="absolute bottom-24 right-6 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card shadow-lg transition-all hover:bg-muted hover:scale-105">
      <ArrowDown className="h-3.5 w-3.5 text-muted-foreground" />
    </ThreadPrimitive.ScrollToBottom>
  );
}

function Composer() {
  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-xl px-4 pb-4 pt-3">
      <ComposerPrimitive.Root className="mx-auto flex w-full max-w-2xl items-end gap-2 rounded-2xl border border-border bg-card p-3 shadow-sm transition-colors focus-within:border-primary/40">
        <ComposerPrimitive.Input
          placeholder="Ask Iris anything about equity research..."
          rows={1}
          autoFocus
          className={cn(
            "flex-1 resize-none bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/60",
            "max-h-40 min-h-9"
          )}
        />
        <ThreadPrimitive.If running>
          <ComposerPrimitive.Cancel className="flex h-8 w-8 items-center justify-center rounded-xl bg-destructive text-white transition-all hover:bg-destructive/80 hover:scale-105">
            <Square className="h-3.5 w-3.5" />
          </ComposerPrimitive.Cancel>
        </ThreadPrimitive.If>
        <ThreadPrimitive.If running={false}>
          <ComposerPrimitive.Send className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-white transition-all hover:bg-primary/80 hover:scale-105 disabled:opacity-20 disabled:hover:scale-100">
            <SendHorizontal className="h-3.5 w-3.5" />
          </ComposerPrimitive.Send>
        </ThreadPrimitive.If>
      </ComposerPrimitive.Root>
    </div>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="relative flex w-full max-w-2xl gap-3 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary ring-1 ring-primary/20">
        U
      </div>
      <div className="flex-1 space-y-1 pt-0.5">
        <MessagePrimitive.Content
          components={{ Text: ({ text }) => <p className="text-sm leading-relaxed text-foreground">{text}</p> }}
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
      <ActionBarPrimitive.Edit className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
        <Pencil className="h-3 w-3" />
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="relative flex w-full max-w-2xl gap-3 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-primary to-indigo-400 text-xs font-bold text-white shadow-sm shadow-primary/20">
        I
      </div>
      <div className="flex-1 space-y-1 pt-0.5">
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
      <ActionBarPrimitive.Copy className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
        <Copy className="h-3 w-3" />
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
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
      <BranchPickerPrimitive.Previous className="flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-muted hover:text-foreground">
        <ChevronLeft className="h-3 w-3" />
      </BranchPickerPrimitive.Previous>
      <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      <BranchPickerPrimitive.Next className="flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-muted hover:text-foreground">
        <ChevronRight className="h-3 w-3" />
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
}
