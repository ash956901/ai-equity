import { useEffect, useState } from "react";
import { EmailVerifyView } from "./EmailVerifyView";
import { ForgotPasswordView } from "./ForgotPasswordView";
import { LoginView } from "./LoginView";
import { ResetPasswordView } from "./ResetPasswordView";
import { SignUpView } from "./SignUpView";

type AuthView = "login" | "signup" | "forgot" | "reset" | "verify";

function readInitialView(): AuthView {
  const params = new URLSearchParams(window.location.search);
  const path = window.location.pathname.toLowerCase();
  if (params.get("token") && path.includes("verify")) {
    return "verify";
  }
  if (params.get("token") && path.includes("reset")) {
    return "reset";
  }
  if (path.includes("verify-email") || path.includes("verify")) return "verify";
  if (path.includes("signup")) return "signup";
  if (path.includes("forgot")) return "forgot";
  return "login";
}

export function AuthGate() {
  const [view, setView] = useState<AuthView>(readInitialView);

  useEffect(() => {
    document.body.classList.add("auth-active");
    return () => {
      document.body.classList.remove("auth-active");
    };
  }, []);

  if (view === "signup") return <SignUpView onSwitch={(v) => setView(v)} />;
  if (view === "forgot") return <ForgotPasswordView onSwitch={(v) => setView(v)} />;
  if (view === "reset") return <ResetPasswordView onSwitch={(v) => setView(v)} />;
  if (view === "verify") return <EmailVerifyView onSwitch={(v) => setView(v)} />;
  return <LoginView onSwitch={(v) => setView(v)} />;
}
