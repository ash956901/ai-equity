import { useState } from "react";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";

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

interface ThinkingMessage {
  thinkingDurationSec?: number;
  executionPlan?: string[];
  agentEvents?: AgentEvent[];
  toolCalls?: ToolCallEvent[];
}

interface ThinkingDropdownProps {
  message: ThinkingMessage;
}

export function ThinkingDropdown({ message }: ThinkingDropdownProps) {
  const [open, setOpen] = useState(false);
  const hasTrace = !!(message.agentEvents?.length || message.toolCalls?.length);
  if (!hasTrace && !message.executionPlan?.length) return null;

  const durationLabel =
    message.thinkingDurationSec != null
      ? message.thinkingDurationSec < 1
        ? "Thought for <1 sec"
        : `Thought for ${message.thinkingDurationSec} sec${message.thinkingDurationSec !== 1 ? "s" : ""}`
      : "Thought process";

  return (
    <div className="thinking-dropdown">
      <button
        type="button"
        className="thinking-toggle"
        onClick={() => setOpen((v) => !v)}
      >
        <Brain size={14} />
        <span>{durationLabel}</span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {open && (
        <div className="thinking-details">
          {message.executionPlan?.length ? (
            <div className="thinking-section">
              <span className="thinking-label">Plan</span>
              <span className="thinking-plan-flow">
                {message.executionPlan.map((step, i) => (
                  <span key={`${step}-${i}`} className="thinking-plan-step">
                    {i > 0 && <span className="thinking-arrow">→</span>}
                    {step}
                  </span>
                ))}
              </span>
            </div>
          ) : null}
          {message.agentEvents?.length ? (
            <div className="thinking-section">
              <span className="thinking-label">Agents</span>
              <div className="thinking-events">
                {message.agentEvents.map((ev, i) => (
                  <div key={`${ev.agent}-${ev.event}-${i}`} className="thinking-event-row">
                    <span className={`thinking-event-dot ${ev.event}`} />
                    <span className="thinking-event-agent">{ev.agent}</span>
                    <span className="thinking-event-status">{ev.event}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {message.toolCalls?.length ? (
            <div className="thinking-section">
              <span className="thinking-label">Tool calls</span>
              <div className="thinking-events">
                {message.toolCalls.map((tc, i) => (
                  <div key={`${tc.agent}-${tc.tool}-${i}`} className="thinking-event-row">
                    <span className={`thinking-event-dot ${tc.status}`} />
                    <span className="thinking-event-agent">{tc.agent}</span>
                    <span className="thinking-event-tool">.{tc.tool}</span>
                    <span className={`thinking-tool-status ${tc.status}`}>{tc.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
