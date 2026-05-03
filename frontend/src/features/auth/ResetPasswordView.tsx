import { useEffect, useState, type FormEvent } from "react";
import { resetPassword } from "../../shared/api/auth";
import { AuthShell } from "./AuthShell";

interface ResetPasswordViewProps {
  onSwitch: (view: "login") => void;
}

export function ResetPasswordView({ onSwitch }: ResetPasswordViewProps) {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (t) setToken(t);
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    if (!token) {
      setError("Reset token is missing.");
      return;
    }
    setBusy(true);
    try {
      await resetPassword({ token, new_password: password });
      setDone(true);
    } catch {
      setError("Reset failed. The token may be invalid or expired.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Set a new password"
      subtitle={
        done
          ? "Your password has been updated. Please sign in."
          : "Enter your new password to finish the reset."
      }
      footer={
        <div className="auth-card__footer-row">
          <button type="button" className="auth-link" onClick={() => onSwitch("login")}>
            Back to sign in
          </button>
        </div>
      }
    >
      {!done ? (
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="auth-field">
            <span>Reset token</span>
            <input value={token} onChange={(e) => setToken(e.target.value)} required />
          </label>
          <label className="auth-field">
            <span>New password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </label>
          {error ? <div className="auth-error">{error}</div> : null}
          <button type="submit" className="auth-submit" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
        </form>
      ) : null}
    </AuthShell>
  );
}
