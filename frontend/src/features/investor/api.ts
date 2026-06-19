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
}

export interface InvestorDashboard {
  profile: InvestorProfile | null;
  onboarding: OnboardingStatus | null;
  portfolios: PortfolioSummary[];
  total_invested_paise: number;
}

export interface HoldingDetail {
  security_symbol: string;
  security_isin: string;
  sector: string | null;
  quantity: number;
  avg_cost_paise: number;
  cost_value_paise: number;
}

export interface CashEntry {
  entry_type: string;
  amount_paise: number;
  balance_paise: number;
  posted_on: string;
}

export const investorApi = {
  dashboard: () =>
    apiClient.get<InvestorDashboard>("/investor/dashboard").then((r) => r.data),
  holdings: (accountId: string) =>
    apiClient.get<HoldingDetail[]>(`/investor/holdings/${accountId}`).then((r) => r.data),
  cash: (accountId: string) =>
    apiClient.get<CashEntry[]>(`/investor/cash/${accountId}`).then((r) => r.data),
};
