import { useState } from "react";
import { usePortfolio, useHoldings, useTrades, useCashLedger } from "../hooks/usePortfolio";
import type { HoldingRow, TradeRow, CashLedgerEntry } from "../types";

type Tab = "overview" | "holdings" | "trades" | "cash";

export default function PortfolioDetail({ accountId }: { accountId: string }) {
  const [tab, setTab] = useState<Tab>("overview");
  const { data: portfolio, isLoading } = usePortfolio(accountId);
  const { data: holdings = [] } = useHoldings(accountId);
  const { data: trades = [] } = useTrades(accountId);
  const { data: ledger = [] } = useCashLedger(accountId);

  if (isLoading) return <p style={{ color: "var(--text-secondary)" }}>Loading...</p>;
  if (!portfolio) return null;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "holdings", label: `Holdings (${portfolio.holdings_count})` },
    { key: "trades", label: "Trades" },
    { key: "cash", label: "Cash Ledger" },
  ];

  return (
    <div>
      {/* Tab bar */}
      <div style={{ display: "flex", gap: 0, borderBottom: "2px solid var(--border)", marginBottom: 20 }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: "10px 20px", fontSize: 14, fontWeight: 500, cursor: "pointer",
              background: "none", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--primary)" : "2px solid transparent",
              color: tab === t.key ? "var(--primary)" : "var(--text-secondary)",
              marginBottom: -2,
            }}
          >{t.label}</button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab portfolio={portfolio} />}
      {tab === "holdings" && <HoldingsTab holdings={holdings} />}
      {tab === "trades" && <TradesTab trades={trades} />}
      {tab === "cash" && <CashTab entries={ledger} />}
    </div>
  );
}

function OverviewTab({ portfolio }: { portfolio: any }) {
  const fmt = (v: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);
  return (
    <div className="card">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Stat label="Account Code" value={portfolio.account_code} />
        <Stat label="Strategy" value={portfolio.strategy_name || "—"} />
        <Stat label="Status" value={portfolio.status} badge />
        <Stat label="Inception" value={portfolio.inception_date} />
        <Stat label="Cash Balance" value={fmt(portfolio.cash_balance_inr)} highlight />
        <Stat label="Invested Value" value={fmt(portfolio.invested_value_inr ?? 0)} />
        <Stat label="Holdings" value={String(portfolio.holdings_count)} />
      </div>
    </div>
  );
}

function Stat({ label, value, badge, highlight }: { label: string; value: string; badge?: boolean; highlight?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>{label}</div>
      {badge ? (
        <span className={`badge badge-${value === "active" ? "success" : "warning"}`}>{value}</span>
      ) : (
        <div style={{ fontSize: 16, fontWeight: highlight ? 700 : 500 }}>{value}</div>
      )}
    </div>
  );
}

function HoldingsTab({ holdings }: { holdings: HoldingRow[] }) {
  const fmt = (v: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(v);
  if (holdings.length === 0) {
    return <div className="card" style={{ textAlign: "center", color: "var(--text-secondary)" }}>No holdings yet.</div>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th><th>ISIN</th><th>Qty</th>
            <th>Avg Cost</th><th>Total Cost</th><th>Lots</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h: HoldingRow) => (
            <tr key={h.security_id}>
              <td style={{ fontWeight: 600 }}>{h.symbol || h.name}</td>
              <td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{h.isin}</td>
              <td>{fmt(h.quantity)}</td>
              <td>{fmt(h.avg_cost_paise / 100)}</td>
              <td>{fmt((h.total_cost_paise ?? h.avg_cost_paise * h.quantity) / 100)}</td>
              <td>{h.lots_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradesTab({ trades }: { trades: TradeRow[] }) {
  const fmt = (v: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(v);
  if (trades.length === 0) {
    return <div className="card" style={{ textAlign: "center", color: "var(--text-secondary)" }}>No trades yet.</div>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr>
            <th>Date</th><th>Side</th><th>Security</th>
            <th>Qty</th><th>Price</th><th>Value</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t: TradeRow) => (
            <tr key={t.id}>
              <td style={{ fontSize: 13 }}>{new Date(t.traded_at).toLocaleDateString("en-IN")}</td>
              <td>
                <span className={`badge badge-${t.side === "buy" ? "success" : "error"}`}>{t.side.toUpperCase()}</span>
              </td>
              <td>{t.symbol || t.security_name}</td>
              <td>{fmt(t.quantity)}</td>
              <td>{fmt(t.price_inr)}</td>
              <td style={{ fontWeight: 600 }}>{fmt(t.value_inr)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CashTab({ entries }: { entries: CashLedgerEntry[] }) {
  const fmt = (v: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);
  if (entries.length === 0) {
    return <div className="card" style={{ textAlign: "center", color: "var(--text-secondary)" }}>No cash entries yet.</div>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr><th>Date</th><th>Type</th><th>Amount</th><th>Description</th></tr>
        </thead>
        <tbody>
          {entries.map((e: CashLedgerEntry, i: number) => (
            <tr key={i}>
              <td style={{ fontSize: 13 }}>{e.posted_on}</td>
              <td><span className="badge">{e.entry_type}</span></td>
              <td style={{ fontWeight: 600, color: e.amount_inr >= 0 ? "var(--success)" : "var(--error)" }}>
                {fmt(e.amount_inr)}
              </td>
              <td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{e.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
