export interface Client {
  id: string;
  client_code: string;
  full_name: string;
  email: string;
  investor_type: string;
  status: string;
}

export interface PortfolioAccount {
  id: string;
  account_code: string;
  strategy_name?: string;
  status: string;
  inception_date: string;
  cash_balance_inr: number;
  invested_value_inr?: number;
  holdings_count: number;
}

export interface HoldingRow {
  security_id: string;
  isin: string;
  symbol: string;
  name: string;
  quantity: number;
  avg_cost_inr: number;
  total_cost_inr: number;
  lots_count: number;
}

export interface TradeRow {
  id: string;
  side: string;
  security_name: string;
  symbol: string;
  quantity: number;
  price_inr: number;
  value_inr: number;
  traded_at: string;
}

export interface CashLedgerEntry {
  entry_type: string;
  amount_inr: number;
  posted_on: string;
  description: string;
}

export interface Security {
  id: string;
  isin: string;
  symbol: string;
  name: string;
  sector: string;
}

export interface Strategy {
  id: string;
  name: string;
  approach: string;
}
