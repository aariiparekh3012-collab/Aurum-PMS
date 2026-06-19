import { apiClient } from "./apiClient";
import type {
  Application,
  ApplicationResponse,
  Broker,
  CashLedgerEntry,
  CashEntry,
  Client,
  DashboardData,
  FeedResponse,
  FeeInvoice,
  Holding,
  HoldingDetail,
  InvestorDashboard,
  KycDetails,
  Order,
  PerformanceReport,
  PerformanceReturn,
  PerformanceSummary,
  PersonalDetails,
  PortfolioAccount,
  PortfolioStatement,
  ReviewApplication,
  ReviewListResponse,
  RiskAnswer,
  Security,
  Snapshot,
  Strategy,
  Trade,
  TransactionReport,
} from "./types";

export const dashboardApi = {
  get: () => apiClient.get<DashboardData>("/dashboard").then((r) => r.data),
};

export const onboardingApi = {
  createApplication: (body: PersonalDetails) =>
    apiClient.post<ApplicationResponse>("/onboarding/applications", body).then((r) => r.data),
  submitKyc: (id: string, body: KycDetails) =>
    apiClient.post<ApplicationResponse>(`/onboarding/applications/${id}/kyc`, body).then((r) => r.data),
  completeRiskProfile: (id: string, answers: RiskAnswer[]) =>
    apiClient.post<ApplicationResponse>(`/onboarding/applications/${id}/risk-profile`, { answers }).then((r) => r.data),
  confirmEsign: (id: string, transactionId: string) =>
    apiClient.post<ApplicationResponse>(`/onboarding/applications/${id}/esign/confirm`, { transaction_id: transactionId }).then((r) => r.data),
};

export const applicationsApi = {
  list: (status?: string) =>
    apiClient.get<Application[]>("/onboarding/applications", { params: status ? { status } : {} }).then((r) => r.data),
  decide: (id: string, approve: boolean, reason?: string) =>
    apiClient.post(`/onboarding/applications/${id}/decision`, { approve, reason }).then((r) => r.data),
};

export const clientsApi = {
  list: () => apiClient.get<Client[]>("/clients").then((r) => r.data),
  get: (id: string) => apiClient.get<Client>(`/clients/${id}`).then((r) => r.data),
  processOutbox: () => apiClient.post<{ processed: number }>("/clients/process-outbox").then((r) => r.data),
};

// ── Portfolio ──
export const portfolioApi = {
  listAccounts: (clientId?: string) =>
    apiClient.get<PortfolioAccount[]>("/portfolio/accounts", { params: clientId ? { client_id: clientId } : {} }).then((r) => r.data),
  getAccount: (id: string) =>
    apiClient.get<PortfolioAccount>(`/portfolio/accounts/${id}`).then((r) => r.data),
  listHoldings: (accountId: string) =>
    apiClient.get<Holding[]>(`/portfolio/accounts/${accountId}/holdings`).then((r) => r.data),
  listCashLedger: (accountId: string) =>
    apiClient.get<CashLedgerEntry[]>(`/portfolio/accounts/${accountId}/cash`).then((r) => r.data),
};

// ── Trading ──
export const tradingApi = {
  listOrders: (status?: string) =>
    apiClient.get<Order[]>("/trading/orders", { params: status ? { status } : {} }).then((r) => r.data),
  createOrder: (body: { strategy_id: string; security_id: string; side: string; quantity: number; order_type?: string; limit_price_paise?: number }) =>
    apiClient.post<Order>("/trading/orders", body).then((r) => r.data),
  decideOrder: (id: string, approve: boolean, reason?: string) =>
    apiClient.post<Order>(`/trading/orders/${id}/decide`, { approve, reason }).then((r) => r.data),
  listTrades: (portfolioAccountId?: string) =>
    apiClient.get<Trade[]>("/trading/trades", { params: portfolioAccountId ? { portfolio_account_id: portfolioAccountId } : {} }).then((r) => r.data),
};

// ── Reference ──
export const referenceApi = {
  listSecurities: (q?: string) =>
    apiClient.get<Security[]>("/reference/securities", { params: q ? { q } : {} }).then((r) => r.data),
  listStrategies: () =>
    apiClient.get<Strategy[]>("/reference/strategies").then((r) => r.data),
  listBrokers: () =>
    apiClient.get<Broker[]>("/reference/brokers").then((r) => r.data),
  seed: () =>
    apiClient.post("/reference/seed").then((r) => r.data),
};

// ── Investor ──
export const investorApi = {
  dashboard: () =>
    apiClient.get<InvestorDashboard>("/investor/dashboard").then((r) => r.data),
  holdings: (accountId: string) =>
    apiClient.get<HoldingDetail[]>(`/investor/holdings/${accountId}`).then((r) => r.data),
  cash: (accountId: string) =>
    apiClient.get<CashEntry[]>(`/investor/cash/${accountId}`).then((r) => r.data),
};

// ── Notifications ──
export const notificationsApi = {
  feed: (entityType?: string, limit = 30, offset = 0) =>
    apiClient.get<FeedResponse>("/notifications/feed", {
      params: { entity_type: entityType || undefined, limit, offset },
    }).then((r) => r.data),
  unreadCount: () =>
    apiClient.get<{ count: number }>("/notifications/unread-count").then((r) => r.data),
  markAllRead: () =>
    apiClient.post("/notifications/mark-read").then((r) => r.data),
  markOneRead: (id: string) =>
    apiClient.post("/notifications/mark-read/" + id).then((r) => r.data),
};

// ── Performance ──
export const performanceApi = {
  summary: (accountId: string) =>
    apiClient.get<PerformanceSummary>(`/performance/summary/${accountId}`).then((r) => r.data),
  snapshots: (accountId: string) =>
    apiClient.get<Snapshot[]>("/performance/snapshots", { params: { portfolio_account_id: accountId } }).then((r) => r.data),
  returns: (accountId: string) =>
    apiClient.get<PerformanceReturn[]>("/performance/returns", { params: { portfolio_account_id: accountId } }).then((r) => r.data),
};

// ── Compliance ──
export const complianceApi = {
  listForReview: (limit = 50, offset = 0) =>
    apiClient.get<ReviewListResponse>("/onboarding/applications/review/pending", { params: { limit, offset } }).then((r) => r.data),
  getApplicationDetail: (id: string) =>
    apiClient.get<ReviewApplication>(`/onboarding/applications/${id}`).then((r) => r.data),
  approveApplication: (id: string, reason?: string) =>
    apiClient.post(`/onboarding/applications/${id}/decision`, { approve: true, reason }).then((r) => r.data),
  rejectApplication: (id: string, reason: string) =>
    apiClient.post(`/onboarding/applications/${id}/decision`, { approve: false, reason }).then((r) => r.data),
};

// ── Reports ──
export const reportsApi = {
  portfolioStatement: (accountId: string) =>
    apiClient.get<PortfolioStatement>("/reports/portfolio-statement/" + accountId).then((r) => r.data),
  transactions: (accountId: string, fromDate: string, toDate: string) =>
    apiClient.get<TransactionReport>("/reports/transactions/" + accountId, {
      params: { from_date: fromDate, to_date: toDate },
    }).then((r) => r.data),
  performance: (accountId: string) =>
    apiClient.get<PerformanceReport>("/reports/performance/" + accountId).then((r) => r.data),
  feeInvoice: (accountId: string, periodFrom: string, periodTo: string) =>
    apiClient.get<FeeInvoice>("/reports/fee-invoice/" + accountId, {
      params: { period_from: periodFrom, period_to: periodTo },
    }).then((r) => r.data),
};
