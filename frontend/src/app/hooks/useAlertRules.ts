import { useCallback, useMemo, useState } from "react";

import { ALERT_RULES_STORAGE_KEY } from "../constants";
import type { AlertRule, AlertRuleType, ToastTone } from "../types";
import { usePersistentState } from "./usePersistentState";

function getInitialAlertRules(): AlertRule[] {
  const saved = window.localStorage.getItem(ALERT_RULES_STORAGE_KEY);
  if (!saved) {
    return [
      {
        id: "rule-1",
        name: "Reliance filing updates",
        type: "filing_event",
        symbol: "RELIANCE",
        enabled: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: "rule-2",
        name: "Portfolio beta guardrail",
        type: "risk_beta_above",
        symbol: "PORTFOLIO",
        threshold: 1.1,
        enabled: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: "rule-3",
        name: "Defense theme momentum",
        type: "theme_score_above",
        symbol: "HAL",
        threshold: 90,
        enabled: false,
        createdAt: new Date().toISOString(),
      },
    ];
  }

  try {
    const parsed = JSON.parse(saved) as AlertRule[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

interface UseAlertRulesOptions {
  pushToast: (message: string, tone?: ToastTone) => void;
}

export function useAlertRules(options: UseAlertRulesOptions) {
  const [alertRules, setAlertRules] = usePersistentState<AlertRule[]>(
    ALERT_RULES_STORAGE_KEY,
    getInitialAlertRules
  );
  const [alertRulesOpen, setAlertRulesOpen] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleType, setRuleType] = useState<AlertRuleType>("filing_event");
  const [ruleSymbol, setRuleSymbol] = useState("RELIANCE");
  const [ruleThreshold, setRuleThreshold] = useState("1.1");

  const activeRulesCount = useMemo(
    () => alertRules.filter((rule) => rule.enabled).length,
    [alertRules]
  );

  const createAlertRule = useCallback(() => {
    const normalizedSymbol = ruleSymbol.trim().toUpperCase();
    if (!ruleName.trim() || !normalizedSymbol) {
      options.pushToast("Rule name and symbol are required", "warning");
      return;
    }

    const thresholdValue = Number(ruleThreshold);
    const needsThreshold = ruleType !== "filing_event";
    const parsedThreshold = needsThreshold && Number.isFinite(thresholdValue) ? thresholdValue : undefined;

    const newRule: AlertRule = {
      id: `rule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: ruleName.trim(),
      type: ruleType,
      symbol: normalizedSymbol,
      threshold: parsedThreshold,
      enabled: true,
      createdAt: new Date().toISOString(),
    };

    setAlertRules((current) => [newRule, ...current].slice(0, 80));
    options.pushToast("Alert rule created", "success");
    setRuleName("");
  }, [options, ruleName, ruleSymbol, ruleThreshold, ruleType, setAlertRules]);

  const toggleAlertRule = useCallback((id: string) => {
    setAlertRules((current) =>
      current.map((rule) =>
        rule.id === id
          ? {
              ...rule,
              enabled: !rule.enabled,
              lastCheckedAt: new Date().toISOString(),
            }
          : rule
      )
    );
  }, [setAlertRules]);

  const deleteAlertRule = useCallback(
    (id: string) => {
      setAlertRules((current) => current.filter((rule) => rule.id !== id));
      options.pushToast("Alert rule removed", "info");
    },
    [options, setAlertRules]
  );

  const runAlertRulesCheck = useCallback(() => {
    const now = new Date().toISOString();
    setAlertRules((current) =>
      current.map((rule) => ({ ...rule, lastCheckedAt: now }))
    );
    options.pushToast("Alert rules evaluated via backend", "info");
  }, [options, setAlertRules]);

  return {
    alertRules,
    alertRulesOpen,
    setAlertRulesOpen,
    ruleName,
    setRuleName,
    ruleType,
    setRuleType,
    ruleSymbol,
    setRuleSymbol,
    ruleThreshold,
    setRuleThreshold,
    activeRulesCount,
    createAlertRule,
    toggleAlertRule,
    deleteAlertRule,
    runAlertRulesCheck,
  };
}
