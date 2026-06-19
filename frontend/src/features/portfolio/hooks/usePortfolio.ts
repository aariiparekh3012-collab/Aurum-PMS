import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/portfolioApi";

export const useClients = () =>
  useQuery({ queryKey: ["clients"], queryFn: api.listClients });

export const usePortfolios = (clientId: string) =>
  useQuery({
    queryKey: ["portfolios", clientId],
    queryFn: () => api.listPortfolios(clientId),
    enabled: !!clientId,
  });

export const usePortfolio = (id: string) =>
  useQuery({
    queryKey: ["portfolio", id],
    queryFn: () => api.getPortfolio(id),
    enabled: !!id,
  });

export const useHoldings = (accountId: string) =>
  useQuery({
    queryKey: ["holdings", accountId],
    queryFn: () => api.getHoldings(accountId),
    enabled: !!accountId,
  });

export const useTrades = (accountId: string) =>
  useQuery({
    queryKey: ["trades", accountId],
    queryFn: () => api.listTrades(accountId),
    enabled: !!accountId,
  });

export const useCashLedger = (accountId: string) =>
  useQuery({
    queryKey: ["cashLedger", accountId],
    queryFn: () => api.getCashLedger(accountId),
    enabled: !!accountId,
  });

export const useSecurities = () =>
  useQuery({ queryKey: ["securities"], queryFn: api.listSecurities });

export const useStrategies = () =>
  useQuery({ queryKey: ["strategies"], queryFn: api.listStrategies });

export const useRecordTrade = (accountId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { security_id: string; side: string; quantity: number; price_inr: number }) =>
      api.recordTrade(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["holdings", accountId] });
      qc.invalidateQueries({ queryKey: ["trades", accountId] });
      qc.invalidateQueries({ queryKey: ["portfolio", accountId] });
      qc.invalidateQueries({ queryKey: ["cashLedger", accountId] });
    },
  });
};

export const useRecordCapitalFlow = (accountId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { flow_type: string; amount_inr: number }) =>
      api.recordCapitalFlow(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio", accountId] });
      qc.invalidateQueries({ queryKey: ["cashLedger", accountId] });
    },
  });
};

export const useCreatePortfolio = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createPortfolio,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolios"] }),
  });
};
