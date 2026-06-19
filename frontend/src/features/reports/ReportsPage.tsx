import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, Button } from "../../components/ui";
import { portfolioApi, PortfolioAccount } from "../portfolio/api";
import { referenceApi } from "../reference/api";
import {
  reportsApi,
  PortfolioStatement,
  TransactionReport,
  PerformanceReport,
  FeeInvoice,
} from "./apiClient";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);

const pctFmt = (n: number) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";

function downloadCsv(filename: string, rows: string[][]) {
  const csv = rows.map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

type ReportKey = "portfolio_statement" | "transaction_report" | "performance_report" | "fee_invoice";

const REPORT_OPTIONS: { key: ReportKey; label: string; desc: string; needsDates: boolean }[] = [
  { key: "portfolio_statement", label: "Portfolio Statement", desc: "Current holdings, valuations, cash ledger", needsDates: false },
  { key: "transaction_report", label: "Transaction Report", desc: "Trade history for a date range", needsDates: true },
  { key: "performance_report", label: "Performance Report", desc: "Returns, benchmarks, valuation history", needsDates: false },
  { key: "fee_invoice", label: "Fee Invoice", desc: "Management & performance fee calculation", needsDates: true },
];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function thirtyDaysAgo() {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Sub-renderers for each report type
// ---------------------------------------------------------------------------

function PortfolioStatementView({ data }: { data: PortfolioStatement }) {
  const exportCsv = () => {
    const header = ["Symbol", "ISIN", "Sector", "Qty", "Avg Cost", "Value", "Weight %"];
    const rows = data.holdings.map((h) => [
      h.security_symbol, h.security_isin, h.sector || "", String(h.quantity),
      String(h.avg_cost_paise / 100), String(h.market_value_paise / 100), String(h.weight_pct),
    ]);
    downloadCsv(data.account_code + "_statement.csv", [header, ...rows]);
  };

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <div>
          <h2>{data.account_code} — {data.strategy_name}</h2>
          <span className="muted">As of {data.as_of} · Inception {data.inception_date}</span>
        </div>
        <Button variant="ghost" onClick={exportCsv}>Export CSV</Button>
      </div>
      <div className="kpis" style={{ marginBottom: 20 }}>
        <div className="kpi"><span className="kpi__value">{inr(data.market_value_paise)}</span><span className="kpi__label">Market value</span></div>
        <div className="kpi"><span className="kpi__value">{inr(data.cost_value_paise)}</span><span className="kpi__label">Cost basis</span></div>
        <div className="kpi">
          <span className="kpi__value" style={{ color: data.unrealised_pnl_paise >= 0 ? "var(--success)" : "var(--danger)" }}>
            {inr(data.unrealised_pnl_paise)}
          </span>
          <span className="kpi__label">Unrealised P&L</span>
        </div>
        <div className="kpi"><span className="kpi__value">{inr(data.cash_paise)}</span><span className="kpi__label">Cash</span></div>
      </div>
      <Card style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 12 }}>Holdings ({data.holdings.length})</h3>
        {data.holdings.length === 0 ? <div className="empty">No holdings</div> : (
          <table className="table">
            <thead><tr><th>Symbol</th><th>ISIN</th><th>Sector</th><th>Qty</th><th>Avg Cost</th><th>Value</th><th>Wt%</th></tr></thead>
            <tbody>
              {data.holdings.map((h) => (
                <tr key={h.security_isin}>
                  <td style={{ fontWeight: 600 }}>{h.security_symbol}</td>
                  <td className="muted">{h.security_isin}</td>
                  <td>{h.sector || "—"}</td>
                  <td>{h.quantity}</td>
                  <td>{inr(h.avg_cost_paise)}</td>
                  <td>{inr(h.market_value_paise)}</td>
                  <td>{h.weight_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {data.cash_ledger.length > 0 && (
        <Card>
          <h3 style={{ marginBottom: 12 }}>Cash Ledger (recent)</h3>
          <table className="table">
            <thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Balance</th></tr></thead>
            <tbody>
              {data.cash_ledger.map((c, i) => (
                <tr key={i}>
                  <td>{c.posted_on}</td>
                  <td>{c.entry_type}</td>
                  <td>{inr(c.amount_paise)}</td>
                  <td>{inr(c.balance_paise)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function TransactionReportView({ data }: { data: TransactionReport }) {
  const exportCsv = () => {
    const header = ["Date", "Symbol", "ISIN", "Side", "Qty", "Price", "Value", "Broker", "Contract"];
    const rows = data.trades.map((t) => [
      t.traded_at.slice(0, 10), t.security_symbol, t.security_isin, t.side,
      String(t.quantity), String(t.price_paise / 100), String(t.value_paise / 100),
      t.broker_name, t.contract_note || "",
    ]);
    downloadCsv(data.account_code + "_transactions.csv", [header, ...rows]);
  };

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <div>
          <h2>{data.account_code} — Transactions</h2>
          <span className="muted">{data.from_date} to {data.to_date} · {data.trade_count} trades</span>
        </div>
        <Button variant="ghost" onClick={exportCsv}>Export CSV</Button>
      </div>
      <div className="kpis" style={{ marginBottom: 20 }}>
        <div className="kpi"><span className="kpi__value">{inr(data.total_buy_value_paise)}</span><span className="kpi__label">Total buys</span></div>
        <div className="kpi"><span className="kpi__value">{inr(data.total_sell_value_paise)}</span><span className="kpi__label">Total sells</span></div>
        <div className="kpi"><span className="kpi__value">{data.trade_count}</span><span className="kpi__label">Trades</span></div>
      </div>
      {data.trades.length === 0 ? <div className="empty">No trades in this period.</div> : (
        <table className="table">
          <thead><tr><th>Date</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Value</th><th>Broker</th></tr></thead>
          <tbody>
            {data.trades.map((t, i) => (
              <tr key={i}>
                <td>{t.traded_at.slice(0, 10)}</td>
                <td style={{ fontWeight: 600 }}>{t.security_symbol}</td>
                <td style={{ color: t.side === "BUY" ? "var(--success)" : "var(--danger)" }}>{t.side}</td>
                <td>{t.quantity}</td>
                <td>{inr(t.price_paise)}</td>
                <td>{inr(t.value_paise)}</td>
                <td className="muted">{t.broker_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function PerformanceReportView({ data }: { data: PerformanceReport }) {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2>{data.account_code} — Performance</h2>
        <span className="muted">{data.strategy_name} · Inception {data.inception_date}</span>
      </div>
      <div className="kpis" style={{ marginBottom: 20 }}>
        <div className="kpi"><span className="kpi__value">{inr(data.latest_market_value_paise)}</span><span className="kpi__label">Market value</span></div>
        <div className="kpi"><span className="kpi__value">{inr(data.latest_cost_value_paise)}</span><span className="kpi__label">Cost basis</span></div>
        <div className="kpi">
          <span className="kpi__value" style={{ color: data.unrealised_pnl_paise >= 0 ? "var(--success)" : "var(--danger)" }}>
            {inr(data.unrealised_pnl_paise)}
          </span>
          <span className="kpi__label">Unrealised P&L</span>
        </div>
      </div>
      {data.returns.length > 0 && (
        <Card style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 12 }}>Returns</h3>
          <table className="table">
            <thead><tr><th>Period</th><th>TWRR</th><th>Benchmark</th><th>Alpha</th></tr></thead>
            <tbody>
              {data.returns.map((r) => (
                <tr key={r.period}>
                  <td style={{ fontWeight: 600 }}>{r.period}</td>
                  <td style={{ color: r.twrr_pct >= 0 ? "var(--success)" : "var(--danger)" }}>{pctFmt(r.twrr_pct)}</td>
                  <td>{r.benchmark_pct != null ? pctFmt(r.benchmark_pct) : "—"}</td>
                  <td style={{ color: r.alpha_pct != null && r.alpha_pct >= 0 ? "var(--success)" : "var(--danger)" }}>
                    {r.alpha_pct != null ? pctFmt(r.alpha_pct) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {data.valuation_history.length > 0 && (
        <Card>
          <h3 style={{ marginBottom: 12 }}>Valuation History ({data.valuation_history.length} snapshots)</h3>
          <table className="table">
            <thead><tr><th>Date</th><th>Market Value</th><th>Cost</th><th>Cash</th></tr></thead>
            <tbody>
              {data.valuation_history.slice(-20).map((s) => (
                <tr key={s.as_of}>
                  <td>{s.as_of}</td>
                  <td>{inr(s.market_value_paise)}</td>
                  <td>{inr(s.cost_value_paise)}</td>
                  <td>{inr(s.cash_paise)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function FeeInvoiceView({ data }: { data: FeeInvoice }) {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2>{data.account_code} — Fee Invoice</h2>
        <span className="muted">{data.strategy_name} · {data.period_from} to {data.period_to}</span>
      </div>
      <div className="kpis" style={{ marginBottom: 20 }}>
        <div className="kpi"><span className="kpi__value">{inr(data.aum_paise)}</span><span className="kpi__label">AUM</span></div>
        <div className="kpi"><span className="kpi__value">{data.fee_schedule_name}</span><span className="kpi__label">Fee schedule</span></div>
      </div>
      <Card style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 12 }}>Fee Breakdown</h3>
        <table className="table">
          <thead><tr><th>Description</th><th>Basis</th><th>Rate</th><th>Amount</th></tr></thead>
          <tbody>
            {data.items.map((item, i) => (
              <tr key={i}>
                <td>{item.description}</td>
                <td>{inr(item.basis_paise)}</td>
                <td>{item.rate_pct}%</td>
                <td style={{ fontWeight: 600 }}>{inr(item.amount_paise)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card>
        <table className="table">
          <tbody>
            <tr><td>Subtotal</td><td style={{ fontWeight: 600, textAlign: "right" }}>{inr(data.total_paise)}</td></tr>
            <tr><td>GST (18%)</td><td style={{ textAlign: "right" }}>{inr(data.gst_paise)}</td></tr>
            <tr style={{ borderTop: "2px solid var(--border)" }}>
              <td style={{ fontWeight: 700 }}>Grand Total</td>
              <td style={{ fontWeight: 700, textAlign: "right", color: "var(--color-gold, #d4af37)" }}>{inr(data.grand_total_paise)}</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function ReportsPage() {
  const [reportType, setReportType] = useState<ReportKey | "">("");
  const [accountId, setAccountId] = useState("");
  const [fromDate, setFromDate] = useState(thirtyDaysAgo());
  const [toDate, setToDate] = useState(today());
  const [trigger, setTrigger] = useState(0);

  const { data: accounts = [] } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.accounts(),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.strategies(),
  });

  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));
  const selectedOpt = REPORT_OPTIONS.find((o) => o.key === reportType);
  const canGenerate = reportType && accountId;

  const { data: reportData, isLoading, error } = useQuery<any>({
    queryKey: ["report", reportType, accountId, fromDate, toDate, trigger],
    queryFn: () => {
      if (!reportType || !accountId) return null;
      switch (reportType) {
        case "portfolio_statement": return reportsApi.portfolioStatement(accountId);
        case "transaction_report": return reportsApi.transactions(accountId, fromDate, toDate);
        case "performance_report": return reportsApi.performance(accountId);
        case "fee_invoice": return reportsApi.feeInvoice(accountId, fromDate, toDate);
        default: return null;
      }
    },
    enabled: trigger > 0 && !!reportType && !!accountId,
  });

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1>Reports</h1>
        <p className="muted">Generate portfolio statements, transaction reports, and fee invoices</p>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 16 }}>Configure Report</h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
          <div>
            <label className="label">Report type</label>
            <select
              className="input"
              value={reportType}
              onChange={(e) => { setReportType(e.target.value as ReportKey); setTrigger(0); }}
            >
              <option value="">— Select report —</option>
              {REPORT_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>{o.label}</option>
              ))}
            </select>
            {selectedOpt && <div className="muted" style={{ marginTop: 4, fontSize: ".82rem" }}>{selectedOpt.desc}</div>}
          </div>

          <div>
            <label className="label">Portfolio account</label>
            <select className="input" value={accountId} onChange={(e) => { setAccountId(e.target.value); setTrigger(0); }}>
              <option value="">— Select account —</option>
              {accounts.map((a: PortfolioAccount) => (
                <option key={a.id} value={a.id}>
                  {a.account_code} ({stratMap[a.strategy_id] || "Strategy"})
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedOpt?.needsDates && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div>
              <label className="label">From date</label>
              <input className="input" type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
            </div>
            <div>
              <label className="label">To date</label>
              <input className="input" type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
            </div>
          </div>
        )}

        <Button
          variant="primary"
          disabled={!canGenerate}
          onClick={() => setTrigger((t) => t + 1)}
        >
          Generate Report
        </Button>
      </Card>

      {isLoading && <div className="empty"><span className="spinner" /> Generating report...</div>}

      {error && <div className="empty" style={{ color: "var(--danger)" }}>Error generating report. Please check your selections.</div>}

      {reportData && reportType === "portfolio_statement" && (
        <Card><PortfolioStatementView data={reportData as PortfolioStatement} /></Card>
      )}
      {reportData && reportType === "transaction_report" && (
        <Card><TransactionReportView data={reportData as TransactionReport} /></Card>
      )}
      {reportData && reportType === "performance_report" && (
        <Card><PerformanceReportView data={reportData as PerformanceReport} /></Card>
      )}
      {reportData && reportType === "fee_invoice" && (
        <Card><FeeInvoiceView data={reportData as FeeInvoice} /></Card>
      )}
    </div>
  );
}
