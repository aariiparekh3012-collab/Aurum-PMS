import { z } from "zod";

// ── Dashboard ──
export interface StatusCount { status: string; count: number; }
export interface RiskCount { category: string; count: number; }
export interface DashboardData {
  total_clients: number;
  active_clients: number;
  total_applications: number;
  pending_review: number;
  applications_by_status: StatusCount[];
  clients_by_risk: RiskCount[];
}

// ── Applications ──
export interface Application {
  id: string;
  status: string;
  investor_type: string;
  full_name: string;
  email: string;
  pan: string;
  proposed_investment_inr: number;
  risk_category: string | null;
  kyc_source: string | null;
}

// ── Clients ──
export interface BankAccount {
  ifsc: string;
  holder_name: string;
  masked_account: string;
  is_primary: boolean;
}
export interface Nominee {
  name: string;
  share_percent: number;
  rank: number;
  relationship: string | null;
}
export interface Client {
  id: string;
  client_code: string;
  status: string;
  investor_type: string;
  full_name: string;
  email: string;
  mobile: string;
  pan: string;
  onboarding_application_id: string;
  risk_category: string | null;
  demat_bo_ids: string[];
  bank_accounts: BankAccount[];
  nominees: Nominee[];
}

// ── Onboarding ──
export interface ApplicationResponse {
  id: string;
  status: string;
  investor_type: string;
  full_name: string;
  email: string;
  pan: string;
  proposed_investment_inr: number;
  risk_category: string | null;
  kyc_source: string | null;
}

export interface RiskAnswer {
  question_id: string;
  weight: number;
}

// ── Portfolio ──
export interface PortfolioAccount {
  id: string;
  client_id: string;
  strategy_id: string;
  account_code: string;
  status: string;
  inception_date: string;
  created_at: string;
}
export interface Holding {
  id: string;
  portfolio_account_id: string;
  security_id: string;
  quantity: number;
  avg_cost_paise: number;
}
export interface CashLedgerEntry {
  id: string;
  portfolio_account_id: string;
  entry_type: string;
  amount_paise: number;
  balance_paise: number;
  posted_on: string;
}

// ── Trading ──
export interface Order {
  id: string;
  strategy_id: string;
  security_id: string;
  side: string;
  quantity: number;
  order_type: string;
  limit_price_paise: number | null;
  status: string;
  created_at: string;
}
export interface Trade {
  id: string;
  order_id: string | null;
  portfolio_account_id: string;
  security_id: string;
  broker_id: string;
  side: string;
  quantity: number;
  price_paise: number;
  traded_at: string;
  contract_note: string | null;
}

// ── Reference ──
export interface Security {
  id: string;
  isin: string;
  symbol: string;
  exchange: string;
  instrument_type: string;
  sector: string | null;
  is_active: boolean;
}
export interface Strategy {
  id: string;
  name: string;
  code: string;
  approach: string;
  benchmark_id: string | null;
  is_active: boolean;
}
export interface Broker {
  id: string;
  name: string;
  sebi_reg_no: string;
  is_active: boolean;
}

// ── Investor Portal ──
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

// ── Notifications ──
export interface Activity {
  id: string;
  actor_role: string;
  actor_subject: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: string | null;
  is_read: boolean;
  created_at: string;
}
export interface FeedResponse {
  items: Activity[];
  total: number;
  unread: number;
}

// ── Performance ──
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

// ── Compliance ──
export interface ReviewApplication {
  id: string;
  full_name: string;
  email: string;
  mobile: string;
  investor_type: string;
  proposed_investment_inr: number;
  status: string;
  risk_category: string | null;
  pan: string;
  created_at: string;
  updated_at: string;
}
export interface ReviewListResponse {
  applications: ReviewApplication[];
  total: number;
  limit: number;
  offset: number;
}

// ── Reports ──
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

// ── Validation ──
export const personalDetailsSchema = z.object({
  investor_type: z.string().min(1),
  full_name: z.string().min(2).max(200),
  email: z.string().email(),
  mobile: z.string().regex(/^[6-9]\d{9}$/, "Enter a valid 10-digit mobile"),
  pan: z.string().regex(/^[A-Z]{5}[0-9]{4}[A-Z]$/, "Invalid PAN"),
  proposed_investment_inr: z.coerce.number().min(5_000_000, "Minimum is ₹50,00,000"),
});
export type PersonalDetails = z.infer<typeof personalDetailsSchema>;

export const kycSchema = z.object({
  aadhaar_full: z.string().regex(/^[2-9][0-9]{11}$/, "Invalid Aadhaar"),
  bank_account_number: z.string().regex(/^\d{8,18}$/, "Invalid account number"),
  bank_ifsc: z.string().regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, "Invalid IFSC"),
  bank_holder_name: z.string().min(2),
  demat_bo_id: z.string().regex(/^\d{16}$/, "16-digit BO id"),
  demat_depository: z.enum(["NSDL", "CDSL"]),
});
export type KycDetails = z.infer<typeof kycSchema>;
