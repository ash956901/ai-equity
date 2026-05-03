import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

interface RequireAuthProps {
  children: ReactNode;
  /** Component to render when no user is authenticated. */
  fallback: ReactNode;
}

export function RequireAuth({ children, fallback }: RequireAuthProps) {
  const { user, loading, initialised } = useAuth();

  if (!initialised || loading) {
    return (
      <div className="auth-loader">
        <p>Loading…</p>
      </div>
    );
  }

  if (!user) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
