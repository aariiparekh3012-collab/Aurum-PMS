import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { auth } from "@/lib/auth";
import { apiClient } from "@/lib/apiClient";

interface User { sub: string; role: string }
interface AuthCtx {
  user: User | null;
  login: (username: string, role: string) => Promise<void>;
  logout: () => void;
  /** Re-reads stored auth state — call after external login flows (features/auth/LoginPage). */
  refresh: () => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

function userFromStorage(): User | null {
  const token = auth.getToken();
  const stored = auth.getUser();
  if (!token || !stored) return null;
  return { sub: stored.subject, role: stored.role };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(userFromStorage);

  /** Legacy dev-token login (stub LoginPage flow). */
  const login = useCallback(async (username: string, role: string) => {
    const { data } = await apiClient.post("/auth/token", { username, role });
    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    auth.setSession(data.access_token, { subject: payload.sub, role: payload.role });
    setUser({ sub: payload.sub, role: payload.role });
  }, []);

  const logout = useCallback(() => {
    auth.clear();
    setUser(null);
  }, []);

  /** Sync context state with whatever lib/auth has stored (e.g. after full JWT login). */
  const refresh = useCallback(() => {
    setUser(userFromStorage());
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
