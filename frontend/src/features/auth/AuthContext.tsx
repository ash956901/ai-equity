import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  fetchMe,
  logoutAuth,
  refreshAuth,
  sendOtp as apiSendOtp,
  verifyOtp as apiVerifyOtp,
  type AuthUser,
} from "./authApi";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  sendOtp: (email: string, purpose: "signup" | "login") => Promise<void>;
  verifyOtp: (
    email: string,
    otp: string,
    purpose: "signup" | "login",
    fullName?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      try {
        await refreshAuth();
      } catch {
        // No valid refresh token — not logged in
      }

      if (cancelled) return;

      try {
        const me = await fetchMe();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    checkSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!user) return;

    const interval = setInterval(async () => {
      try {
        await refreshAuth();
      } catch {
        setUser(null);
      }
    }, 25 * 60 * 1000); // refresh every 25 min

    return () => clearInterval(interval);
  }, [user]);

  const sendOtp = useCallback(
    async (email: string, purpose: "signup" | "login") => {
      await apiSendOtp(email, purpose);
    },
    [],
  );

  const verifyOtp = useCallback(
    async (
      email: string,
      otp: string,
      purpose: "signup" | "login",
      fullName?: string,
    ) => {
      const result = await apiVerifyOtp(email, otp, purpose, fullName);
      setUser(result.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await logoutAuth();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      sendOtp,
      verifyOtp,
      logout,
      refreshUser,
    }),
    [user, isLoading, sendOtp, verifyOtp, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
