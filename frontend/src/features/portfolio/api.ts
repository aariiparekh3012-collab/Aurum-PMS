import { apiClient } from "../../lib/apiClient";

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

export const portfolioApi = {
  accounts: (clientId?: string) =>
    apiClient.get<PortfolioAccount[]>("/portfolio/accounts", {
      params: clientId ? { client_id: clientId } : {},
    }).then((r) => r.data),

  createAccount: (data: {
    client_id: string;
    strategy_id: string;
    account_code: string;
    inception_date: string;
  }) => apiClient.post<PortfolioAccount>("/portfolio/accounts", data).then((r) => r.data),

  holdings: (accountId: string) =>
    apiClient.get<Holding[]>("/portfolio/accounts/" + accountId + "/holdings").then((r) => r.data),
};
