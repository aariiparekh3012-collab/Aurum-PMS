import { apiClient } from "../../lib/apiClient";

export interface InvestorProfile {
  client_id: string;
  full_name: string;
  client_code: string;
  pan: string;
  email: string;
  status: string;
  risk_category: string | null;
  investor_type: string;
}

export interface OnboardingStatus {
  id: string;
  status: string;
  full_name: string;
  pan: string;
  proposed_investment_inr: number;
  kyc_source: string | null;
  risk_category: string | null;
}

export interface PortfolioSummary {
  account_id: string;
  account_code: string;
  strategy_name: string;
  status: string;
  inception_date: string;
  holdings_count: number;
  total_cost_paise: number;
  market_value_paise: number;
  cash_balance_paise: number;
  unrealised_pnl_paise: number;
}

export interface PerformanceReturn {
  period: string;
  twrr_pct: number;
  mwrr_pct: number | null;
  benchmark_pct: number | null;
  as_of: string;
}

export interface InvestorDashboard {
  profile: InvestorProfile | null;
  onboarding: OnboardingStatus | null;
  portfolios: PortfolioSummary[];
  total_invested_paise: number;
  total_market_value_paise: number;
  total_unrealised_pnl_paise: number;
  total_cash_paise: number;
  returns: PerformanceReturn[];
}

export interface HoldingDetail {
  security_symbol: string;
  security_isin: string;
  sector: string | null;
  quantity: number;
  avg_cost_paise: number;
  cost_value_paise: number;
  market_price_paise: number;
  market_value_paise: number;
  unrealised_pnl_paise: number;
  day_change_pct: number;
}

export interface CashEntry {
  entry_type: string;
  amount_paise: number;
  balance_paise: number;
  posted_on: string;
}

export interface ValuationPoint {
  as_of: string;
  market_value_paise: number;
  cost_value_paise: number;
  cash_paise: number;
}

export interface FeeEntry {
  entry_type: string;
  amount_paise: number;
  posted_on: string;
  description: string;
}

export interface DocumentInfo {
  id: string;
  document_type: string;
  uploaded_at: string;
  download_url: string | null;
}

export const investorApi = {
  dashboard: () =>
    apiClient.get<InvestorDashboard>("/investor/dashboard").then((r) => r.data),
  holdings: (accountId: string) =>
    apiClient.get<HoldingDetail[]>(`/investor/holdings/${accountId}`).then((r) => r.data),
  cash: (accountId: string) =>
    apiClient.get<CashEntry[]>(`/investor/cash/${accountId}`).then((r) => r.data),
  valuationHistory: (accountId: string) =>
    apiClient.get<ValuationPoint[]>(`/investor/valuation-history/${accountId}`).then((r) => r.data),
  fees: (accountId: string) =>
    apiClient.get<FeeEntry[]>(`/investor/fees/${accountId}`).then((r) => r.data),
  documents: () =>
    apiClient.get<DocumentInfo[]>("/investor/documents").then((r) => r.data),
};
