import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { portfolioApi } from "../api";

export const useClients = () =>
  useQuery({ queryKey: ["clients"], queryFn: portfolioApi.listClients });

export const usePortfolios = (clientId: string) =>
  useQuery({
    queryKey: ["portfolios", clientId],
    queryFn: () => portfolioApi.accounts(clientId),
    enabled: !!clientId,
  });

export const usePortfolio = (id: string) =>
  useQuery({
    queryKey: ["portfolio", id],
    queryFn: () => portfolioApi.getAccount(id),
    enabled: !!id,
  });

export const useHoldings = (accountId: string) =>
  useQuery({
    queryKey: ["holdings", accountId],
    queryFn: () => portfolioApi.holdings(accountId),
    enabled: !!accountId,
  });

export const useTrades = (accountId: string) =>
  useQuery({
    queryKey: ["trades", accountId],
    queryFn: () => portfolioApi.listTrades(accountId),
    enabled: !!accountId,
  });

export const useCashLedger = (accountId: string) =>
  useQuery({
    queryKey: ["cashLedger", accountId],
    queryFn: () => portfolioApi.cashLedger(accountId),
    enabled: !!accountId,
  });

export const useSecurities = () =>
  useQuery({ queryKey: ["securities"], queryFn: portfolioApi.securities });

export const useStrategies = () =>
  useQuery({ queryKey: ["strategies"], queryFn: portfolioApi.strategies });

export const useRecordTrade = (accountId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { security_id: string; side: string; quantity: number; price_inr: number }) =>
      portfolioApi.recordTrade(accountId, data),
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
      portfolioApi.recordCapitalFlow(accountId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio", accountId] });
      qc.invalidateQueries({ queryKey: ["cashLedger", accountId] });
    },
  });
};

export const useCreatePortfolio = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: portfolioApi.createAccount,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolios"] }),
  });
};
