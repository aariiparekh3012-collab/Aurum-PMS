import { apiClient } from "../../lib/apiClient";

export interface Snapshot {
  id: string;
  portfolio_account_id: string;
  as_of: string;
  market_value_paise: number;
  cost_value_paise: number;
  cash_paise: number;
}

export interface PerformanceReturn {
  id: string;
  portfolio_account_id: string;
  period: string;
  as_of: string;
  twrr_pct: number;
  benchmark_pct: number | null;
}

export interface PerformanceSummary {
  latest_market_value_paise: number;
  latest_cost_value_paise: number;
  latest_cash_paise: number;
  unrealised_pnl_paise: number;
  returns: PerformanceReturn[];
  history: Snapshot[];
}

export const performanceApi = {
  summary: (accountId: string) =>
    apiClient.get<PerformanceSummary>(`/performance/summary/${accountId}`).then((r) => r.data),
  snapshots: (accountId: string) =>
    apiClient.get<Snapshot[]>("/performance/snapshots", { params: { portfolio_account_id: accountId } }).then((r) => r.data),
  returns: (accountId: string) =>
    apiClient.get<PerformanceReturn[]>("/performance/returns", { params: { portfolio_account_id: accountId } }).then((r) => r.data),
};
