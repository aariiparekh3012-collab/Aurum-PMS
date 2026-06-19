import { apiClient } from "../../lib/apiClient";

export interface StatusCount {
  status: string;
  count: number;
}

export interface RiskCount {
  category: string;
  count: number;
}

export interface DashboardData {
  total_clients: number;
  active_clients: number;
  total_applications: number;
  pending_review: number;
  total_aum_paise: number;
  total_portfolio_accounts: number;
  pending_orders: number;
  applications_by_status: StatusCount[];
  clients_by_risk: RiskCount[];
}

export const dashboardApi = {
  get: () => apiClient.get<DashboardData>("/dashboard").then((r) => r.data),
};
