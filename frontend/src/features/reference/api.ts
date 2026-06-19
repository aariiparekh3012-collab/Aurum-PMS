import { apiClient } from "../../lib/apiClient";

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

export interface Benchmark {
  id: string;
  name: string;
  code: string;
}

export interface FeeSchedule {
  id: string;
  name: string;
  mgmt_fee_pct: number;
  perf_fee_pct: number;
  high_water_mark: boolean;
  hurdle_rate_pct: number | null;
}

export const referenceApi = {
  securities: (q = "") =>
    apiClient.get<Security[]>("/reference/securities", { params: { q } }).then((r) => r.data),
  createSecurity: (data: { isin: string; symbol: string; exchange: string; instrument_type: string; sector?: string }) =>
    apiClient.post<Security>("/reference/securities", data).then((r) => r.data),
  strategies: () =>
    apiClient.get<Strategy[]>("/reference/strategies").then((r) => r.data),
  createStrategy: (data: { name: string; code: string; approach: string; benchmark_id?: string }) =>
    apiClient.post<Strategy>("/reference/strategies", data).then((r) => r.data),
  brokers: () =>
    apiClient.get<Broker[]>("/reference/brokers").then((r) => r.data),
  createBroker: (data: { name: string; sebi_reg_no: string }) =>
    apiClient.post<Broker>("/reference/brokers", data).then((r) => r.data),
  benchmarks: () =>
    apiClient.get<Benchmark[]>("/reference/benchmarks").then((r) => r.data),
  createBenchmark: (data: { name: string; code: string }) =>
    apiClient.post<Benchmark>("/reference/benchmarks", data).then((r) => r.data),
  feeSchedules: () =>
    apiClient.get<FeeSchedule[]>("/portfolio/fee-schedules").then((r) => r.data),
  createFeeSchedule: (data: { name: string; mgmt_fee_pct: number; perf_fee_pct: number; high_water_mark: boolean; hurdle_rate_pct?: number }) =>
    apiClient.post<FeeSchedule>("/portfolio/fee-schedules", data).then((r) => r.data),
  seed: () =>
    apiClient.post("/reference/seed").then((r) => r.data),
};
