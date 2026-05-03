import { useEffect, useState } from "react";
import { verifyEmail } from "../../shared/api/auth";
import { AuthShell } from "./AuthShell";

interface EmailVerifyViewProps {
  onSwitch: (view: "login") => void;
}

type Phase = "verifying" | "success" | "error" | "missing";

export function EmailVerifyView({ onSwitch }: EmailVerifyViewProps) {
  const [phase, setPhase] = useState<Phase>("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (!token) {
      setPhase("missing");
      return;
    }
    let cancelled = false;
    verifyEmail(token)
      .then(() => {
        if (!cancelled) setPhase("success");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message ?? "Verification failed");
        setPhase("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  let subtitle: string;
  if (phase === "verifying") subtitle = "Verifying your email…";
  else if (phase === "success") subtitle = "Your email is verified. Please sign in.";
  else if (phase === "missing") subtitle = "No verification token found in the URL.";
  else subtitle = error || "The verification token is invalid or expired.";

  return (
    <AuthShell
      title="Verify email"
      subtitle={subtitle}
      footer={
        <div className="auth-card__footer-row">
          <button type="button" className="auth-link" onClick={() => onSwitch("login")}>
            Back to sign in
          </button>
        </div>
      }
    >
      {phase === "error" ? <div className="auth-error">{error}</div> : null}
      {phase === "success" ? (
        <button
          type="button"
          className="auth-submit"
          onClick={() => onSwitch("login")}
        >
          Continue to sign in
        </button>
      ) : null}
    </AuthShell>
  );
}
