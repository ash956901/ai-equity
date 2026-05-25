import { useCallback, useEffect, useState } from "react";
import { fetchTransactions, topupBalance } from "../../shared/api/platform";
import { fetchUserProfile } from "../../shared/api/user";
import type { UserProfile, UserTransaction } from "../../shared/types/api";

const PRESET_AMOUNTS = [100_000, 500_000, 1_000_000];

function formatInr(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function MoneyView() {
  const userId = localStorage.getItem("equityai-user-id") ?? "";

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [transactions, setTransactions] = useState<UserTransaction[]>([]);
  const [customAmount, setCustomAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [topping, setTopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const [prof, txns] = await Promise.all([
        fetchUserProfile(userId),
        fetchTransactions(userId, 50),
      ]);
      setProfile(prof);
      setTransactions(txns);
    } catch {
      setError("Could not load account data. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleTopup = useCallback(
    async (amount: number) => {
      if (!userId || amount <= 0) return;
      setTopping(true);
      setError(null);
      setSuccessMsg(null);
      try {
        const result = await topupBalance(userId, amount);
        setProfile((prev) =>
          prev ? { ...prev, simulation_balance: result.simulation_balance } : prev
        );
        setSuccessMsg(`${formatInr(amount)} added to your simulation account.`);
        const txns = await fetchTransactions(userId, 50);
        setTransactions(txns);
        setCustomAmount("");
      } catch {
        setError("Failed to add funds. Please try again.");
      } finally {
        setTopping(false);
      }
    },
    [userId]
  );

  const handleCustomTopup = useCallback(() => {
    const parsed = parseFloat(customAmount.replace(/,/g, ""));
    if (isNaN(parsed) || parsed <= 0) {
      setError("Enter a valid amount greater than 0.");
      return;
    }
    void handleTopup(parsed);
  }, [customAmount, handleTopup]);

  return (
    <div className="page-wrap">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--ink)", margin: 0 }}>
          Manage Money
        </h1>
        <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: "0.88rem" }}>
          Simulation account balance, top-up, and transaction history
        </p>
      </div>

      {error && (
        <div className="notice warning" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}
      {successMsg && (
        <div className="notice success" style={{ marginBottom: 16 }}>
          {successMsg}
        </div>
      )}

      {/* Balance card */}
      <div
        className="list-card"
        style={{
          padding: "28px 32px",
          marginBottom: 20,
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Simulation Balance
        </p>
        {loading ? (
          <p style={{ margin: 0, fontSize: "2.4rem", fontWeight: 700, color: "var(--ink)" }}>—</p>
        ) : (
          <p style={{ margin: 0, fontSize: "2.4rem", fontWeight: 700, color: "var(--brand)" }}>
            {formatInr(profile?.simulation_balance ?? 0)}
          </p>
        )}
        <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.8rem" }}>
          For paper-trading only — not real money
        </p>
      </div>

      {/* Add Funds */}
      <div className="list-card" style={{ padding: "20px 24px", marginBottom: 20 }}>
        <p style={{ margin: "0 0 14px", fontWeight: 600, color: "var(--ink)", fontSize: "0.95rem" }}>
          Add Funds
        </p>
        <div className="chip-row" style={{ marginBottom: 14, flexWrap: "wrap" }}>
          {PRESET_AMOUNTS.map((amt) => (
            <button
              key={amt}
              type="button"
              className="secondary-btn"
              disabled={topping}
              onClick={() => void handleTopup(amt)}
              style={{ minWidth: 90 }}
            >
              + {amt >= 100_000 ? `₹${amt / 100_000}L` : `₹${amt.toLocaleString("en-IN")}`}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            className="search-input"
            placeholder="Custom amount (e.g. 250000)"
            value={customAmount}
            onChange={(e) => setCustomAmount(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCustomTopup();
            }}
            style={{ flex: 1, maxWidth: 280 }}
            type="number"
            min={1}
          />
          <button
            type="button"
            className="primary-btn"
            disabled={topping || !customAmount}
            onClick={handleCustomTopup}
          >
            {topping ? "Adding..." : "Add Funds"}
          </button>
        </div>
      </div>

      {/* Transaction History */}
      <div className="list-card" style={{ padding: "20px 24px" }}>
        <p style={{ margin: "0 0 14px", fontWeight: 600, color: "var(--ink)", fontSize: "0.95rem" }}>
          Transaction History
        </p>
        {loading ? (
          <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>Loading...</p>
        ) : transactions.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
            No transactions yet. Add funds above to get started.
          </p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={{ textAlign: "left", padding: "6px 12px 10px 0", color: "var(--muted)", fontWeight: 600 }}>Date</th>
                  <th style={{ textAlign: "left", padding: "6px 12px 10px", color: "var(--muted)", fontWeight: 600 }}>Type</th>
                  <th style={{ textAlign: "right", padding: "6px 0 10px 12px", color: "var(--muted)", fontWeight: 600 }}>Amount</th>
                  <th style={{ textAlign: "right", padding: "6px 0 10px 12px", color: "var(--muted)", fontWeight: 600 }}>Balance After</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <tr
                    key={txn.id}
                    className="list-item"
                    style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}
                  >
                    <td style={{ padding: "10px 12px 10px 0", color: "var(--muted)" }}>
                      {formatDate(txn.created_at)}
                    </td>
                    <td style={{ padding: "10px 12px", color: "var(--ink)", textTransform: "capitalize" }}>
                      {txn.transaction_type}
                    </td>
                    <td style={{ padding: "10px 0 10px 12px", textAlign: "right", color: "var(--brand)", fontWeight: 600 }}>
                      +{formatInr(txn.amount)}
                    </td>
                    <td style={{ padding: "10px 0 10px 12px", textAlign: "right", color: "var(--ink)" }}>
                      {formatInr(txn.balance_after)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
