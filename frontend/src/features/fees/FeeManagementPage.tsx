import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { Card, Button, SkeletonTable, useToast } from "../../components/ui";

interface FeeSchedule {
  id: string;
  name: string;
  mgmt_fee_pct: number;
  perf_fee_pct: number;
  high_water_mark: boolean;
  hurdle_rate_pct: number | null;
}

interface FeeChargeResult {
  portfolio_account_id: string;
  account_code: string;
  mgmt_fee_paise: number;
  perf_fee_paise: number;
  total_fee_paise: number;
  total_fee_inr: number;
  new_cash_balance_paise: number;
}

interface BatchResult {
  as_of: string;
  accounts_charged: number;
  total_fees_paise: number;
  total_fees_inr: number;
  details: FeeChargeResult[];
}

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 2,
  }).format(paise / 100);

export function FeeManagementPage() {
  const _qc = useQueryClient(); void _qc;
  const toast = useToast();
  const [tab, setTab] = useState<"schedules" | "billing" | "history">("schedules");
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ["fee-schedules"],
    queryFn: () =>
      apiClient.get<FeeSchedule[]>("/portfolio/fee-schedules").then((r) => r.data),
  });

  const quarterlyMutation = useMutation({
    mutationFn: () =>
      apiClient.post<BatchResult>("/fees/batch/quarterly").then((r) => r.data),
    onSuccess: (data) => {
      setBatchResult(data);
      toast.success(`Quarterly fees charged: ${data.accounts_charged} accounts`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const perfFeeMutation = useMutation({
    mutationFn: () =>
      apiClient.post<BatchResult>("/fees/batch/annual-performance").then((r) => r.data),
    onSuccess: (data) => {
      setBatchResult(data);
      toast.success(`Performance fees charged: ${data.accounts_charged} accounts`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>Fee Management</h1>
        <p className="muted">Fee schedules, billing runs, and charge history</p>
      </div>

      <div className="row" style={{ gap: 8, marginBottom: 24 }}>
        {(["schedules", "billing", "history"] as const).map((t) => (
          <button
            key={t}
            className={`btn btn--sm ${tab === t ? "btn--primary" : "btn--ghost"}`}
            onClick={() => setTab(t)}
          >
            {t === "schedules" ? "Fee Schedules" : t === "billing" ? "Run Billing" : "Charge History"}
          </button>
        ))}
      </div>

      {tab === "schedules" && (
        <Card>
          <h2 style={{ marginBottom: 16 }}>Fee Schedules</h2>
          {isLoading ? (
            <SkeletonTable rows={3} cols={5} />
          ) : schedules.length === 0 ? (
            <div className="empty">No fee schedules configured yet.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ textAlign: "right" }}>Mgmt Fee %</th>
                  <th style={{ textAlign: "right" }}>Perf Fee %</th>
                  <th>High-Water Mark</th>
                  <th style={{ textAlign: "right" }}>Hurdle Rate %</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 500 }}>{s.name}</td>
                    <td style={{ textAlign: "right" }}>{s.mgmt_fee_pct}%</td>
                    <td style={{ textAlign: "right" }}>{s.perf_fee_pct}%</td>
                    <td>
                      <span className={`badge ${s.high_water_mark ? "badge--success" : ""}`}>
                        {s.high_water_mark ? "Yes" : "No"}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>{s.hurdle_rate_pct ?? "—"}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === "billing" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <Card>
            <h2 style={{ marginBottom: 12 }}>Quarterly Management Fee</h2>
            <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
              Charge management fees (% of AUM) for the last 90 days across all active accounts
              with a fee schedule assigned.
            </p>
            <Button
              variant="primary"
              onClick={() => quarterlyMutation.mutate()}
              disabled={quarterlyMutation.isPending}
            >
              {quarterlyMutation.isPending ? "Running..." : "Run Quarterly Billing"}
            </Button>
          </Card>

          <Card>
            <h2 style={{ marginBottom: 12 }}>Annual Performance Fee</h2>
            <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
              Charge performance fees (gains above high-water mark + hurdle) for all active
              accounts. Typically run at financial year end.
            </p>
            <Button
              variant="primary"
              onClick={() => perfFeeMutation.mutate()}
              disabled={perfFeeMutation.isPending}
            >
              {perfFeeMutation.isPending ? "Running..." : "Run Annual Perf Fee"}
            </Button>
          </Card>

          {batchResult && (
            <Card style={{ gridColumn: "1 / -1" }}>
              <h2 style={{ marginBottom: 16 }}>Billing Results</h2>
              <div className="kpis" style={{ marginBottom: 16 }}>
                <div className="kpi">
                  <span className="kpi__value">{batchResult.accounts_charged}</span>
                  <span className="kpi__label">Accounts charged</span>
                </div>
                <div className="kpi">
                  <span className="kpi__value">{inr(batchResult.total_fees_paise)}</span>
                  <span className="kpi__label">Total fees</span>
                </div>
              </div>

              {batchResult.details.length > 0 && (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th style={{ textAlign: "right" }}>Mgmt Fee</th>
                      <th style={{ textAlign: "right" }}>Perf Fee</th>
                      <th style={{ textAlign: "right" }}>Total</th>
                      <th style={{ textAlign: "right" }}>New Cash Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchResult.details.map((d) => (
                      <tr key={d.portfolio_account_id}>
                        <td className="mono" style={{ fontWeight: 500 }}>{d.account_code}</td>
                        <td style={{ textAlign: "right" }}>{inr(d.mgmt_fee_paise)}</td>
                        <td style={{ textAlign: "right" }}>{inr(d.perf_fee_paise)}</td>
                        <td style={{ textAlign: "right", fontWeight: 600 }}>{inr(d.total_fee_paise)}</td>
                        <td style={{ textAlign: "right" }}>{inr(d.new_cash_balance_paise)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}
        </div>
      )}

      {tab === "history" && (
        <Card>
          <h2 style={{ marginBottom: 16 }}>Fee Charge History</h2>
          <p className="muted">
            Fee charges appear as entries in each account's cash ledger (entry types: mgmt_fee, perf_fee, exit_load).
            View them in the Portfolio → Cash Ledger tab.
          </p>
        </Card>
      )}
    </div>
  );
}
