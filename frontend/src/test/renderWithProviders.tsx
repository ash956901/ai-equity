import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import { AuthProvider } from "../app/state/AuthContext";

interface ProviderOptions extends Omit<RenderOptions, "wrapper"> {
  /** Skip wrapping in AuthProvider (e.g. when stubbing useAuth directly). */
  noAuth?: boolean;
  /** Custom QueryClient to control retry / staleTime in tests. */
  queryClient?: QueryClient;
}

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { noAuth, queryClient, ...options }: ProviderOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const client = queryClient ?? makeClient();

  function Wrapper({ children }: { children: ReactNode }) {
    const tree = (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    return noAuth ? tree : <AuthProvider>{tree}</AuthProvider>;
  }

  const result = render(ui, { wrapper: Wrapper, ...options });
  return { ...result, queryClient: client };
}
