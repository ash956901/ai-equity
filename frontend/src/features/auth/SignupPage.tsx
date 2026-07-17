import { useCallback, useState } from "react";
import { useAuth } from "./AuthContext";

interface SignupPageProps {
  onGoToLogin: () => void;
}

export function SignupPage({ onGoToLogin }: SignupPageProps) {
  const { sendOtp, verifyOtp } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSendOtp = useCallback(async () => {
    if (!email.trim() || !fullName.trim()) return;
    setError("");
    setLoading(true);
    try {
      await sendOtp(email.trim(), "signup");
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
  }, [email, fullName, sendOtp]);

  const handleVerifyOtp = useCallback(async () => {
    if (otp.length !== 6) return;
    setError("");
    setLoading(true);
    try {
      await verifyOtp(email.trim(), otp, "signup", fullName.trim());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid OTP";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [email, otp, fullName, verifyOtp]);

  if (otpSent) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1 className="auth-title">Verify your email</h1>
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
            {loading ? "Creating account..." : "Create Account"}
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
            Edit details
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Create your account</h1>
        <p className="auth-subtitle">Start your equity research journey</p>

        <label className="auth-label" htmlFor="signup-name">
          Full name
        </label>
        <input
          id="signup-name"
          type="text"
          className="auth-input"
          placeholder="John Doe"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          autoFocus
        />

        <label className="auth-label" htmlFor="signup-email">
          Email address
        </label>
        <input
          id="signup-email"
          type="email"
          className="auth-input"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSendOtp();
          }}
        />

        {error && <p className="auth-error">{error}</p>}

        <button
          className="auth-button"
          disabled={!email.trim() || !fullName.trim() || loading}
          onClick={handleSendOtp}
        >
          {loading ? "Sending..." : "Get verification code"}
        </button>

        <p className="auth-footer-text">
          Already have an account?{" "}
          <button className="auth-link-button" onClick={onGoToLogin}>
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}
