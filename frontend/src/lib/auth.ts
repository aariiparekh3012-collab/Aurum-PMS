/** Auth store backed by localStorage (persists across reloads).
 *  Supports both legacy dev-token flow and real JWT + refresh token. */

const TOKEN_KEY = "pms_access_token";
const REFRESH_KEY = "pms_refresh_token";
const USER_KEY = "pms_user";
const EXPIRES_KEY = "pms_token_expires";

export interface AuthUser {
  subject: string;
  role: string;
  id?: string;
  email?: string;
  full_name?: string;
  email_verified?: boolean;
}

export const auth = {
  getToken: (): string | null => localStorage.getItem(TOKEN_KEY),
  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_KEY),
  getUser: (): AuthUser | null => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  },

  /** Store tokens from real auth flow (register/login/refresh). */
  setTokens: (accessToken: string, refreshToken: string, expiresIn: number, user: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
    localStorage.setItem(EXPIRES_KEY, String(Date.now() + expiresIn * 1000));
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  /** Legacy dev-token session (no refresh token). */
  setSession: (token: string, user: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EXPIRES_KEY);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  updateUser: (partial: Partial<AuthUser>) => {
    const current = auth.getUser();
    if (current) {
      localStorage.setItem(USER_KEY, JSON.stringify({ ...current, ...partial }));
    }
  },

  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EXPIRES_KEY);
    localStorage.removeItem(USER_KEY);
  },

  isAuthenticated: (): boolean => !!localStorage.getItem(TOKEN_KEY),

  /** Check if access token is expired or about to expire (within 60s). */
  isTokenExpired: (): boolean => {
    const exp = localStorage.getItem(EXPIRES_KEY);
    if (!exp) return false; // dev-token, no expiry tracking
    return Date.now() > Number(exp) - 60_000;
  },

  hasRefreshToken: (): boolean => !!localStorage.getItem(REFRESH_KEY),
};

export type Role = "compliance" | "relationship_manager" | "investor" | "admin";

export const ROLE_HOME: Record<string, string> = {
  admin: "/dashboard",
  compliance: "/clients",
  relationship_manager: "/applications",
  rm: "/applications", // legacy alias
  investor: "/my-portfolio",
};

export const ROLE_ROUTES: Record<string, string[]> = {
  admin: [
    "/", "/dashboard", "/onboarding", "/applications", "/compliance", "/clients",
    "/securities", "/strategies", "/brokers", "/fee-schedules",
    "/orders", "/trades", "/holdings", "/performance",
    "/reports", "/activity", "/settings", "/audit",
  ],
  compliance: [
    "/", "/dashboard", "/onboarding", "/applications", "/compliance", "/clients",
    "/securities", "/strategies", "/brokers", "/fee-schedules",
    "/orders", "/trades", "/holdings", "/performance",
    "/reports", "/activity", "/settings",
  ],
  relationship_manager: [
    "/", "/dashboard", "/onboarding", "/applications", "/clients",
    "/securities", "/strategies", "/brokers",
    "/orders", "/trades", "/holdings", "/performance",
    "/reports", "/activity", "/settings",
  ],
  rm: [
    "/", "/dashboard", "/onboarding", "/applications", "/clients",
    "/securities", "/strategies", "/brokers",
    "/orders", "/trades", "/holdings", "/performance",
    "/reports", "/activity", "/settings",
  ],
  investor: ["/onboarding", "/my-portfolio", "/reports", "/activity", "/settings"],
};

export const homeFor = (role: string | undefined): string =>
  (role && ROLE_HOME[role]) || "/";

export const canAccess = (role: string | undefined, path: string): boolean => {
  const allowed = (role && ROLE_ROUTES[role]) || [];
  return allowed.some((p) =>
    p === "/" ? path === "/" : path === p || path.startsWith(p + "/")
  );
};

export const hasRole = (role: string): boolean => auth.getUser()?.role === role;
