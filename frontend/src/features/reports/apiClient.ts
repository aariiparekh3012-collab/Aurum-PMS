import { apiClient } from "../../lib/apiClient";

export interface ReportType {
  key: string;
  label: string;
  description: string;
}

export interface HoldingRow {
  security_symbol: string;
  security_isin: string;
  sector: string | null;
  quantity: number;
  avg_cost_paise: number;
  market_value_paise: number;
  weight_pct: number;
}

export interface CashRow {
  posted_on: string;
  entry_type: string;
  amount_paise: number;
  balance_paise: number;
}

export interface PortfolioStatement {
  account_code: string;
  client_id: string;
  strategy_name: string;
  inception_date: string;
  as_of: string;
  market_value_paise: number;
  cost_value_paise: number;
  cash_paise: number;
  unrealised_pnl_paise: number;
  holdings: HoldingRow[];
  cash_ledger: CashRow[];
}

export interface TradeRow {
  traded_at: string;
  security_symbol: string;
  security_isin: string;
  side: string;
  quantity: number;
  price_paise: number;
  value_paise: number;
  broker_name: string;
  contract_note: string | null;
}

export interface TransactionReport {
  account_code: string;
  strategy_name: string;
  from_date: string;
  to_date: string;
  total_buy_value_paise: number;
  total_sell_value_paise: number;
  trade_count: number;
  trades: TradeRow[];
}

export interface ReturnRow {
  period: string;
  as_of: string;
  twrr_pct: number;
  benchmark_pct: number | null;
  alpha_pct: number | null;
}

export interface SnapshotRow {
  as_of: string;
  market_value_paise: number;
  cost_value_paise: number;
  cash_paise: number;
}

export interface PerformanceReport {
  account_code: string;
  strategy_name: string;
  inception_date: string;
  latest_market_value_paise: number;
  latest_cost_value_paise: number;
  unrealised_pnl_paise: number;
  returns: ReturnRow[];
  valuation_history: SnapshotRow[];
}

export interface FeeLineItem {
  description: string;
  basis_paise: number;
  rate_pct: number;
  amount_paise: number;
}

export interface FeeInvoice {
  account_code: string;
  strategy_name: string;
  client_id: string;
  period_from: string;
  period_to: string;
  aum_paise: number;
  fee_schedule_name: string;
  items: FeeLineItem[];
  total_paise: number;
  gst_paise: number;
  grand_total_paise: number;
}

export const reportsApi = {
  types: () => apiClient.get<ReportType[]>("/reports/types").then((r) => r.data),

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
export { apiClient };

