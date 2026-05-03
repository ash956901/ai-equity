import type { ReactNode } from "react";

interface AuthShellProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="auth-shell">
      <div className="auth-card">
        <header className="auth-card__header">
          <span className="auth-card__brand">EquityAI</span>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </header>
        <div className="auth-card__body">{children}</div>
        {footer ? <footer className="auth-card__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}
