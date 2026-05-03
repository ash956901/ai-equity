import { useState, type FormEvent } from "react";
import { forgotPassword } from "../../shared/api/auth";
import { AuthShell } from "./AuthShell";

interface ForgotPasswordViewProps {
  onSwitch: (view: "login") => void;
}

export function ForgotPasswordView({ onSwitch }: ForgotPasswordViewProps) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await forgotPassword(email.trim());
      setDone(true);
    } catch {
      setError("Could not request reset. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Reset your password"
      subtitle={
        done
          ? "If that email exists in our system, a reset link has been sent."
          : "We'll email you a link to choose a new password."
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
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              required
              autoComplete="email"
            />
          </label>
          {error ? <div className="auth-error">{error}</div> : null}
          <button type="submit" className="auth-submit" disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      ) : null}
    </AuthShell>
  );
}
