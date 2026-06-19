import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { performanceApi, Snapshot, PerformanceReturn } from "./api";
import { portfolioApi, PortfolioAccount } from "../portfolio/api";
import { referenceApi } from "../reference/api";
import { Card, SkeletonKPIs, SkeletonTable } from "../../components/ui";
import { AreaChart, MultiLineChart, GaugeChart, DonutChart } from "../../components/charts";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

const inrAxis = (paise: number) => {
  const v = paise / 100;
  if (v >= 1e7) return (v / 1e7).toFixed(1) + "Cr";
  if (v >= 1e5) return (v / 1e5).toFixed(1) + "L";
  return v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
};

const pctFmt = (n: number) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";

export function PerformancePage() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [chartMode, setChartMode] = useState<"value" | "comparison">("value");

  const { data: accounts = [] } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.accounts(),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.strategies(),
  });

  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const { data: summary, isLoading } = useQuery({
    queryKey: ["performance-summary", selectedAccount],
    queryFn: () => (selectedAccount ? performanceApi.summary(selectedAccount) : Promise.resolve(null)),
    enabled: !!selectedAccount,
  });

  const chartData = (summary?.history || []).map((s: Snapshot) => ({
    x: new Date(s.as_of).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
    y: s.market_value_paise,
  }));

  // Build comparison series for multi-line chart (portfolio vs cost basis)
  const comparisonSeries = summary?.history?.length
    ? [
        {
          label: "Market Value",
          color: "#d4af37",
          data: summary.history.map((s: Snapshot) => ({
            x: new Date(s.as_of).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
            y: s.market_value_paise,
          })),
        },
        {
          label: "Cost Basis",
          color: "#60a5fa",
          data: summary.history.map((s: Snapshot) => ({
            x: new Date(s.as_of).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
            y: s.cost_value_paise,
          })),
        },
      ]
    : [];

  const PERIOD_ORDER = ["1M", "3M", "6M", "1Y", "3Y", "SI"];

  // Compute aggregate metrics
  const latestReturn = summary?.returns?.find((r: PerformanceReturn) => r.period === "SI");

  // Asset allocation mock from history (market value vs cash)
  const allocationData = summary
    ? [
        { label: "Equity", value: Math.round(summary.latest_market_value_paise / 100), color: "#d4af37" },
        { label: "Cash", value: Math.round(summary.latest_cash_paise / 100), color: "#9aa7bd" },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <h1>Performance &amp; Analytics</h1>
        <p className="muted">Portfolio valuations, returns, and benchmark comparison</p>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 12 }}>Select portfolio account</h2>
        {accounts.length === 0 ? (
          <div className="empty">No portfolio accounts found.</div>
        ) : (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {accounts.map((a: PortfolioAccount) => (
              <button
                key={a.id}
                className={"btn " + (selectedAccount === a.id ? "btn--primary" : "btn--ghost")}
                onClick={() => setSelectedAccount(a.id)}
              >
                {a.account_code}
                <span className="faint" style={{ marginLeft: 6, fontSize: ".8rem" }}>
                  {stratMap[a.strategy_id] || ""}
                </span>
              </button>
            ))}
          </div>
        )}
      </Card>

      {selectedAccount && isLoading && (
        <div>
          <SkeletonKPIs count={4} />
          <div style={{ marginTop: 24 }}><SkeletonTable rows={4} cols={4} /></div>
        </div>
      )}

      {selectedAccount && summary && (
        <>
          {/* KPIs */}
          <div className="kpis" style={{ marginBottom: 24 }}>
            <div className="kpi">
              <span className="kpi__value">{inr(summary.latest_market_value_paise)}</span>
              <span className="kpi__label">Market value</span>
            </div>
            <div className="kpi">
              <span className="kpi__value">{inr(summary.latest_cost_value_paise)}</span>
              <span className="kpi__label">Cost basis</span>
            </div>
            <div className="kpi">
              <span className="kpi__value" style={{
                color: summary.unrealised_pnl_paise >= 0 ? "var(--success)" : "var(--danger)"
              }}>
                {inr(summary.unrealised_pnl_paise)}
              </span>
              <span className="kpi__label">Unrealised P&amp;L</span>
            </div>
            <div className="kpi">
              <span className="kpi__value">{inr(summary.latest_cash_paise)}</span>
              <span className="kpi__label">Cash balance</span>
            </div>
          </div>

          {/* Charts row */}
          <div className="grid" style={{ gridTemplateColumns: "2fr 1fr", gap: 24, marginBottom: 24 }}>
            <Card>
              <div className="row row--between" style={{ marginBottom: 16 }}>
                <h2 style={{ fontSize: "1rem" }}>Portfolio Value</h2>
                <div className="row" style={{ gap: 4 }}>
                  <button
                    className={`btn btn--xs ${chartMode === "value" ? "btn--primary" : "btn--ghost"}`}
                    onClick={() => setChartMode("value")}
                  >
                    Value
                  </button>
                  <button
                    className={`btn btn--xs ${chartMode === "comparison" ? "btn--primary" : "btn--ghost"}`}
                    onClick={() => setChartMode("comparison")}
                  >
                    vs Cost
                  </button>
                </div>
              </div>
              {chartData.length < 2 ? (
                <div className="empty">Need at least 2 valuation snapshots to show chart.</div>
              ) : chartMode === "value" ? (
                <AreaChart
                  data={chartData}
                  width={600}
                  height={220}
                  formatY={(v) => "₹" + inrAxis(v)}
                  gradientId="perfArea"
                />
              ) : (
                <MultiLineChart
                  series={comparisonSeries}
                  width={600}
                  height={220}
                  formatY={(v) => "₹" + inrAxis(v)}
                />
              )}
            </Card>

            <div style={{ display: "grid", gap: 24 }}>
              <Card>
                <h3 style={{ marginBottom: 12, fontSize: ".92rem" }}>Asset Allocation</h3>
                {allocationData.length > 0 ? (
                  <DonutChart data={allocationData} size={140} />
                ) : (
                  <div className="empty" style={{ fontSize: ".85rem" }}>No data</div>
                )}
              </Card>
              <Card>
                <h3 style={{ marginBottom: 8, fontSize: ".92rem" }}>Return Score</h3>
                <div style={{ display: "flex", justifyContent: "center" }}>
                  <GaugeChart
                    value={latestReturn ? Math.round(Math.min(Math.max(latestReturn.twrr_pct, -50), 50) + 50) : 50}
                    max={100}
                    label={latestReturn ? `SI: ${pctFmt(latestReturn.twrr_pct)}` : "No data"}
                    size={130}
                  />
                </div>
              </Card>
            </div>
          </div>

          {/* Returns table */}
          <Card>
            <h2 style={{ marginBottom: 16 }}>Returns vs Benchmark</h2>
            {summary.returns.length === 0 ? (
              <div className="empty">No return data recorded yet.</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th style={{ textAlign: "right" }}>TWRR</th>
                    <th style={{ textAlign: "right" }}>Benchmark</th>
                    <th style={{ textAlign: "right" }}>Alpha</th>
                  </tr>
                </thead>
                <tbody>
                  {PERIOD_ORDER
                    .map((p) => summary.returns.find((r: PerformanceReturn) => r.period === p))
                    .filter((r): r is PerformanceReturn => !!r)
                    .map((r) => {
                      const alpha = r.benchmark_pct != null ? r.twrr_pct - r.benchmark_pct : null;
                      return (
                        <tr key={r.period}>
                          <td style={{ fontWeight: 600 }}>{r.period}</td>
                          <td style={{ textAlign: "right", color: r.twrr_pct >= 0 ? "var(--success)" : "var(--danger)" }}>
                            {pctFmt(r.twrr_pct)}
                          </td>
                          <td style={{ textAlign: "right" }}>{r.benchmark_pct != null ? pctFmt(r.benchmark_pct) : "—"}</td>
                          <td style={{
                            textAlign: "right",
                            color: alpha != null ? (alpha >= 0 ? "var(--success)" : "var(--danger)") : undefined
                          }}>
                            {alpha != null ? pctFmt(alpha) : "—"}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
