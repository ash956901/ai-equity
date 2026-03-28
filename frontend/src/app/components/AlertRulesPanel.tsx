import { Trash2, X } from "lucide-react";

type AlertRuleType = "filing_event" | "risk_beta_above" | "theme_score_above";

interface AlertRule {
  id: string;
  name: string;
  type: AlertRuleType;
  symbol: string;
  threshold?: number;
  enabled: boolean;
  createdAt: string;
  lastCheckedAt?: string;
  lastTriggeredAt?: string;
}

interface AlertRulesPanelProps {
  open: boolean;
  rules: AlertRule[];
  ruleName: string;
  ruleType: AlertRuleType;
  ruleSymbol: string;
  ruleThreshold: string;
  onClose: () => void;
  onRuleNameChange: (value: string) => void;
  onRuleTypeChange: (value: AlertRuleType) => void;
  onRuleSymbolChange: (value: string) => void;
  onRuleThresholdChange: (value: string) => void;
  onCreateRule: () => void;
  onRunCheck: () => void;
  onToggleRule: (id: string) => void;
  onDeleteRule: (id: string) => void;
}

export function AlertRulesPanel(props: AlertRulesPanelProps) {
  if (!props.open) return null;

  return (
    <div className="favorites-overlay" role="dialog" aria-modal="true" aria-label="Alert rules panel">
      <button
        type="button"
        className="favorites-backdrop"
        onClick={props.onClose}
      />

      <aside className="favorites-panel">
        <div className="notification-panel-head">
          <div>
            <p className="results-title">Automation</p>
            <h3>Alert Rules Builder</h3>
          </div>
          <button
            type="button"
            className="notification-close"
            onClick={props.onClose}
            aria-label="Close alert rules panel"
          >
            <X size={16} />
          </button>
        </div>

        <div className="rule-builder-form">
          <input
            className="rule-input"
            placeholder="Rule name"
            value={props.ruleName}
            onChange={(event) => props.onRuleNameChange(event.target.value)}
          />

          <select
            className="type-select"
            value={props.ruleType}
            onChange={(event) => props.onRuleTypeChange(event.target.value as AlertRuleType)}
          >
            <option value="filing_event">Filing Event</option>
            <option value="risk_beta_above">Risk: Beta Above</option>
            <option value="theme_score_above">Theme Score Above</option>
          </select>

          <input
            className="rule-input"
            placeholder="Symbol (e.g. RELIANCE or PORTFOLIO)"
            value={props.ruleSymbol}
            onChange={(event) => props.onRuleSymbolChange(event.target.value)}
          />

          {props.ruleType !== "filing_event" ? (
            <input
              className="rule-input"
              placeholder="Threshold"
              value={props.ruleThreshold}
              onChange={(event) => props.onRuleThresholdChange(event.target.value)}
            />
          ) : null}

          <div className="rule-actions">
            <button type="button" className="primary-btn" onClick={props.onCreateRule}>
              Add Rule
            </button>
            <button type="button" className="secondary-btn mini-btn" onClick={props.onRunCheck}>
              Run Check
            </button>
          </div>
        </div>

        <div className="notification-list">
          {props.rules.length ? (
            props.rules.map((rule) => (
              <article key={rule.id} className={`notification-item ${rule.enabled ? "unread" : "read"}`}>
                <div className="notification-item-head">
                  <span className="chip notif-system">{rule.type.replace(/_/g, " ")}</span>
                  <span className={`chip ${rule.enabled ? "positive" : ""}`}>
                    {rule.enabled ? "enabled" : "disabled"}
                  </span>
                </div>

                <h4>{rule.name}</h4>
                <p>
                  Symbol: {rule.symbol}
                  {rule.threshold !== undefined ? ` · threshold ${rule.threshold}` : ""}
                </p>
                <small>
                  {rule.lastTriggeredAt
                    ? `Last triggered: ${new Date(rule.lastTriggeredAt).toLocaleString()}`
                    : "Not triggered yet"}
                </small>

                <div className="notification-item-actions">
                  <button
                    type="button"
                    className="secondary-btn mini-btn"
                    onClick={() => props.onToggleRule(rule.id)}
                  >
                    {rule.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    type="button"
                    className="secondary-btn mini-btn"
                    onClick={() => props.onDeleteRule(rule.id)}
                  >
                    <Trash2 size={13} />
                    Delete
                  </button>
                </div>
              </article>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No alert rules created yet.</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
