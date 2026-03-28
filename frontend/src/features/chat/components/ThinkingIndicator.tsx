import { Brain } from "lucide-react";

export function ThinkingIndicator() {
  return (
    <div className="thinking-indicator">
      <Brain size={14} className="thinking-icon-pulse" />
      <span>Thinking</span>
      <span className="thinking-dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
    </div>
  );
}
