import { useCallback, useState } from "react";
import { useAuth } from "./AuthContext";

interface LoginPageProps {
  onGoToSignup: () => void;
}

export function LoginPage({ onGoToSignup }: LoginPageProps) {
  const { sendOtp, verifyOtp } = useAuth();
  const [email, setEmail] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSendOtp = useCallback(async () => {
    if (!email.trim()) return;
    setError("");
    setLoading(true);
    try {
      await sendOtp(email.trim(), "login");
      setOtpSent(true);
      setResendCooldown(60);
      const timer = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send OTP";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [email, sendOtp]);

  const handleVerifyOtp = useCallback(async () => {
    if (otp.length !== 6) return;
    setError("");
    setLoading(true);
    try {
      await verifyOtp(email.trim(), otp, "login");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid OTP";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [email, otp, verifyOtp]);

  if (otpSent) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1 className="auth-title">Check your email</h1>
          <p className="auth-subtitle">
            We sent a 6-digit code to <strong>{email}</strong>
          </p>

          <div className="otp-input-group">
            {Array.from({ length: 6 }).map((_, i) => (
              <input
                key={i}
                type="text"
                inputMode="numeric"
                maxLength={1}
                className="otp-digit"
                value={otp[i] ?? ""}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "");
                  const next = otp.substring(0, i) + val + otp.substring(i + 1);
                  setOtp(next);
                  if (val && e.target.nextElementSibling) {
                    (e.target.nextElementSibling as HTMLInputElement).focus();
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === "Backspace" && !otp[i] && e.currentTarget.previousElementSibling) {
                    (e.currentTarget.previousElementSibling as HTMLInputElement).focus();
                  }
                }}
                onPaste={(e) => {
                  e.preventDefault();
                  const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
                  setOtp(pasted);
                }}
              />
            ))}
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button
            className="auth-button"
            disabled={otp.length !== 6 || loading}
            onClick={handleVerifyOtp}
          >
            {loading ? "Verifying..." : "Verify & Sign In"}
          </button>

          {resendCooldown > 0 ? (
            <p className="auth-resend-text">
              Resend code in {resendCooldown}s
            </p>
          ) : (
            <button
              className="auth-link-button"
              onClick={handleSendOtp}
              disabled={loading}
            >
              Resend OTP
            </button>
          )}

          <button
            className="auth-link-button"
            onClick={() => {
              setOtpSent(false);
              setOtp("");
              setError("");
            }}
          >
            Use a different email
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to your EquityAI account</p>

        <label className="auth-label" htmlFor="login-email">
          Email address
        </label>
        <input
          id="login-email"
          type="email"
          className="auth-input"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSendOtp();
          }}
          autoFocus
        />

        {error && <p className="auth-error">{error}</p>}

        <button
          className="auth-button"
          disabled={!email.trim() || loading}
          onClick={handleSendOtp}
        >
          {loading ? "Sending..." : "Continue with email"}
        </button>

        <p className="auth-footer-text">
          Don't have an account?{" "}
          <button className="auth-link-button" onClick={onGoToSignup}>
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}
