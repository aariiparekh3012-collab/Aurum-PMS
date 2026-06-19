import { apiClient } from "../../lib/apiClient";

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

export const tradingApi = {
  orders: (status?: string) =>
    apiClient.get<Order[]>("/trading/orders", { params: status ? { status } : {} }).then((r) => r.data),
  createOrder: (data: {
    strategy_id: string;
    security_id: string;
    side: string;
    quantity: number;
    order_type?: string;
    limit_price_paise?: number;
  }) => apiClient.post<Order>("/trading/orders", data).then((r) => r.data),
  decideOrder: (id: string, approve: boolean, reason?: string) =>
    apiClient.post<Order>(`/trading/orders/${id}/decide`, { approve, reason }).then((r) => r.data),
  trades: (portfolioAccountId?: string) =>
    apiClient.get<Trade[]>("/trading/trades", {
      params: portfolioAccountId ? { portfolio_account_id: portfolioAccountId } : {},
    }).then((r) => r.data),
  recordTrade: (data: {
    order_id?: string;
    portfolio_account_id: string;
    security_id: string;
    broker_id: string;
    side: string;
    quantity: number;
    price_paise: number;
    contract_note?: string;
  }) => apiClient.post<Trade>("/trading/trades", data).then((r) => r.data),
};
