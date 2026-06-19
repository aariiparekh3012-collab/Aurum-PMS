import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "pms_access_token";
const USER_KEY = "pms_user";

export interface AuthUser {
  subject: string;
  role: string;
}

export type Role = "compliance" | "rm" | "investor";

/** Tabs each role can see (mirrors web ROLE_ROUTES). */
export const ROLE_TABS: Record<string, string[]> = {
  compliance: [
    "DashboardTab", "OnboardingTab", "ApplicationsTab", "ComplianceTab",
    "ClientsTab", "SecuritiesTab", "PortfolioTab", "TradingTab",
    "PerformanceTab", "ReportsTab", "ActivityTab", "SettingsTab", "ProfileTab",
  ],
  rm: [
    "DashboardTab", "OnboardingTab", "ApplicationsTab",
    "ClientsTab", "SecuritiesTab", "PortfolioTab", "TradingTab",
    "PerformanceTab", "ReportsTab", "ActivityTab", "SettingsTab", "ProfileTab",
  ],
  investor: [
    "OnboardingTab", "InvestorTab", "ReportsTab", "ActivityTab", "SettingsTab", "ProfileTab",
  ],
};

export const canSeeTab = (role: string | undefined, tab: string): boolean => {
  const tabs = (role && ROLE_TABS[role]) || [];
  return tabs.includes(tab);
};

let _token: string | null = null;
let _user: AuthUser | null = null;

export const auth = {
  async init() {
    _token = await SecureStore.getItemAsync(TOKEN_KEY);
    const raw = await SecureStore.getItemAsync(USER_KEY);
    _user = raw ? JSON.parse(raw) : null;
  },

  getToken: () => _token,
  getUser: () => _user,
  isAuthenticated: () => !!_token,

  async setSession(token: string, user: AuthUser) {
    _token = token;
    _user = user;
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
  },

  async clear() {
    _token = null;
    _user = null;
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(USER_KEY);
  },
};
