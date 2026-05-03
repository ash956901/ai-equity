import { useState, type FormEvent } from "react";
import { useAuth } from "../../app/state/AuthContext";
import { ApiError } from "../../shared/api/core";
import { AuthShell } from "./AuthShell";

interface SignUpViewProps {
  onSwitch: (view: "login") => void;
}

export function SignUpView({ onSwitch }: SignUpViewProps) {
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setVerifyMessage(null);
    setBusy(true);
    try {
      const result = await signup({
        email: email.trim(),
        username: username.trim() || undefined,
        password,
        full_name: fullName.trim() || undefined,
      });
      if (result.email_verification_required) {
        setVerifyMessage(
          "Account created. Check your email for a verification link before signing in.",
        );
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Could not create account");
      } else {
        setError("Could not create account. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="It takes 30 seconds. Free during the early-access window."
      footer={
        <div className="auth-card__footer-row">
          <span>Already have an account?</span>
          <button
            type="button"
            className="auth-link"
            onClick={() => onSwitch("login")}
          >
            Sign in
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="auth-field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            autoFocus
            required
          />
        </label>
        <label className="auth-field">
          <span>Username (optional)</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="ravi_kapoor"
            autoComplete="username"
            minLength={3}
            maxLength={50}
          />
        </label>
        <label className="auth-field">
          <span>Full name (optional)</span>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="name"
          />
        </label>
        <label className="auth-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>
        {error ? <div className="auth-error">{error}</div> : null}
        {verifyMessage ? <div className="auth-info">{verifyMessage}</div> : null}
        <button type="submit" className="auth-submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
