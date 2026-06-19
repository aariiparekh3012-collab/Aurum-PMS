import { apiClient } from "@/lib/apiClient";

// ── Clients ──
export const provisionClient = (onboardingApplicationId: string) =>
  apiClient.post("/portfolio/clients/provision", {
    onboarding_application_id: onboardingApplicationId,
  }).then(r => r.data);

export const listClients = () =>
  apiClient.get("/portfolio/clients").then(r => r.data.clients);

// ── Portfolio accounts ──
export const createPortfolio = (data: {
  client_id: string; strategy_id: string; fee_schedule_id?: string;
}) => apiClient.post("/portfolio/accounts", data).then(r => r.data);

export const getPortfolio = (id: string) =>
  apiClient.get(`/portfolio/accounts/${id}`).then(r => r.data);

export const listPortfolios = (clientId: string) =>
  apiClient.get("/portfolio/accounts", { params: { client_id: clientId } }).then(r => r.data.accounts);

// ── Holdings ──
export const getHoldings = (accountId: string) =>
  apiClient.get(`/portfolio/accounts/${accountId}/holdings`).then(r => r.data.holdings);

// ── Trades ──
export const recordTrade = (accountId: string, data: {
  security_id: string; side: string; quantity: number; price_inr: number;
}) => apiClient.post(`/portfolio/accounts/${accountId}/trades`, data).then(r => r.data);

export const listTrades = (accountId: string) =>
  apiClient.get(`/portfolio/accounts/${accountId}/trades`).then(r => r.data.trades);

// ── Capital flows ──
export const recordCapitalFlow = (accountId: string, data: {
  flow_type: string; amount_inr: number;
}) => apiClient.post(`/portfolio/accounts/${accountId}/capital-flows`, data).then(r => r.data);

export const getCashLedger = (accountId: string) =>
  apiClient.get(`/portfolio/accounts/${accountId}/cash-ledger`).then(r => r.data.entries);

// ── Reference data ──
export const listSecurities = () =>
  apiClient.get("/portfolio/securities").then(r => r.data.securities);

export const listStrategies = () =>
  apiClient.get("/portfolio/strategies").then(r => r.data.strategies);
