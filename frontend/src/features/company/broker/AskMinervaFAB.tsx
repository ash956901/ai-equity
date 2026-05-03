import { Bot } from "lucide-react";

interface AskMinervaFABProps {
  ticker: string;
  companyName?: string | null;
  onAsk: (prompt: string) => void;
}

export function AskMinervaFAB({ ticker, companyName, onAsk }: AskMinervaFABProps) {
  const handleClick = () => {
    const subject = companyName || ticker.toUpperCase();
    onAsk(
      `Run a deep analysis on ${subject} (ticker ${ticker.toUpperCase()}). ` +
        "Lead with any hidden / asymmetric exposure surfaced by the discovery subagent.",
    );
  };
  return (
    <button type="button" className="ask-minerva-fab" onClick={handleClick} title="Ask Minerva about this company">
      <Bot size={18} />
      <span>Ask Minerva</span>
    </button>
  );
}
