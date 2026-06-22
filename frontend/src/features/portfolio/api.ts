import { apiClient } from "../../lib/apiClient";
import type { PortfolioAccount, HoldingRow } from "./types";

// Re-export for consumers that import types from api.ts
export type { PortfolioAccount } from "./types";
export type { HoldingRow as Holding } from "./types";

// ── API ────────────────────────────────────────────────────────────────────────

export const portfolioApi = {
  // ── Clients ──
  provisionClient: (onboardingApplicationId: string) =>
    apiClient.post("/portfolio/clients/provision", {
      onboarding_application_id: onboardingApplicationId,
    }).then((r) => r.data),

  listClients: () =>
    apiClient.get("/portfolio/clients").then((r) => r.data.clients),

  // ── Portfolio accounts ──
  accounts: (clientId?: string) =>
    apiClient.get("/portfolio/accounts", {
      params: clientId ? { client_id: clientId } : {},
    }).then((r) => r.data as PortfolioAccount[]),

  getAccount: (id: string) =>
    apiClient.get(`/portfolio/accounts/${id}`).then((r) => r.data as PortfolioAccount),

  createAccount: (data: {
    client_id: string;
    strategy_id: string;
    account_code?: string;
    inception_date?: string;
    fee_schedule_id?: string;
  }) => apiClient.post("/portfolio/accounts", data).then((r) => r.data as PortfolioAccount),

  // ── Holdings ──
  holdings: (accountId: string) =>
    apiClient.get(`/portfolio/accounts/${accountId}/holdings`).then((r) => r.data as HoldingRow[]),

  // ── Trades ──
  recordTrade: (accountId: string, data: {
    security_id: string;
    side: string;
    quantity: number;
    price_inr: number;
  }) => apiClient.post(`/portfolio/accounts/${accountId}/trades`, data).then((r) => r.data),

  listTrades: (accountId: string) =>
    apiClient.get(`/portfolio/accounts/${accountId}/trades`).then((r) => r.data.trades),

  // ── Capital flows ──
  recordCapitalFlow: (accountId: string, data: {
    flow_type: string;
    amount_inr: number;
  }) => apiClient.post(`/portfolio/accounts/${accountId}/capital-flows`, data).then((r) => r.data),

  cashLedger: (accountId: string) =>
    apiClient.get(`/portfolio/accounts/${accountId}/cash-ledger`).then((r) => r.data.entries),

  // ── Reference data ──
  securities: () =>
    apiClient.get("/portfolio/securities").then((r) => r.data.securities),

  strategies: () =>
    apiClient.get("/portfolio/strategies").then((r) => r.data.strategies),
};
