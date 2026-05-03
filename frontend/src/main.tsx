import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { AuthGate } from "./features/auth/AuthGate";
import { AuthProvider } from "./app/state/AuthContext";
import { QueryProvider } from "./app/state/QueryProvider";
import { RequireAuth } from "./app/state/RequireAuth";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryProvider>
      <AuthProvider>
        <RequireAuth fallback={<AuthGate />}>
          <App />
        </RequireAuth>
      </AuthProvider>
    </QueryProvider>
  </StrictMode>,
);
