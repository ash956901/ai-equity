import { useState, type FormEvent } from "react";
import { useAuth } from "../../app/state/AuthContext";
import { ApiError } from "../../shared/api/core";
import { AuthShell } from "./AuthShell";

interface LoginViewProps {
  onSwitch: (view: "signup" | "forgot") => void;
}

export function LoginView({ onSwitch }: LoginViewProps) {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(identifier.trim(), password);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Invalid credentials");
      } else {
        setError("Could not sign in. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to access Minerva, Discovery, and your portfolio."
      footer={
        <div className="auth-card__footer-row">
          <button
            type="button"
            className="auth-link"
            onClick={() => onSwitch("forgot")}
          >
            Forgot password?
          </button>
          <span>·</span>
          <button
            type="button"
            className="auth-link"
            onClick={() => onSwitch("signup")}
          >
            Create account
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="auth-field">
          <span>Email or username</span>
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="you@example.com"
            autoComplete="username"
            autoFocus
            required
          />
        </label>
        <label className="auth-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
            minLength={8}
          />
        </label>
        {error ? <div className="auth-error">{error}</div> : null}
        <button type="submit" className="auth-submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}
