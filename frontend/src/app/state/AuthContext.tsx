import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  signup as apiSignup,
  type CurrentUser,
  type SignupResponse,
} from "../../shared/api/auth";
import {
  clearAuthTokens,
  getAccessToken,
  subscribeAuth,
} from "../../shared/api/core";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  initialised: boolean;
}

interface AuthContextValue extends AuthState {
  login: (identifier: string, password: string) => Promise<CurrentUser>;
  signup: (input: {
    email: string;
    username?: string;
    password: string;
    full_name?: string;
  }) => Promise<SignupResponse>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: false,
    initialised: false,
  });
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refreshMe = useCallback(async () => {
    if (!getAccessToken()) {
      if (mounted.current)
        setState({ user: null, loading: false, initialised: true });
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    try {
      const user = await fetchMe();
      if (mounted.current)
        setState({ user, loading: false, initialised: true });
    } catch {
      if (mounted.current) {
        clearAuthTokens();
        setState({ user: null, loading: false, initialised: true });
      }
    }
  }, []);

  useEffect(() => {
    void refreshMe();
    const unsub = subscribeAuth((loggedIn) => {
      if (!loggedIn) {
        setState((s) => ({ ...s, user: null }));
      }
    });
    return () => {
      unsub();
    };
  }, [refreshMe]);

  const login = useCallback(
    async (identifier: string, password: string) => {
      await apiLogin({ identifier, password });
      const user = await fetchMe();
      setState({ user, loading: false, initialised: true });
      return user;
    },
    [],
  );

  const signup = useCallback(
    async (input: {
      email: string;
      username?: string;
      password: string;
      full_name?: string;
    }) => {
      const result = await apiSignup(input);
      if (!result.email_verification_required) {
        const user = await fetchMe();
        setState({ user, loading: false, initialised: true });
      }
      return result;
    },
    [],
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setState({ user: null, loading: false, initialised: true });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, signup, logout, refreshMe }),
    [state, login, signup, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
