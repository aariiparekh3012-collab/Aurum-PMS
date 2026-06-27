import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { portfolioApi, PortfolioAccount, Holding } from "./api";
import { referenceApi } from "../reference/api";
import { clientsApi } from "../clients/api";
import { Card, Button, Toast } from "../../components/ui";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100);

const inrVal = (val: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(val);

// ── Mock holdings for demo ────────────────────────────────────────────────
const MOCK_HOLDINGS: Holding[] = [
  { id: "mock-1", security_id: "s1", isin: "INE002A01018", symbol: "RELIANCE", name: "Reliance Industries", sector: "Energy", quantity: 150, avg_cost_paise: 240000, ltp_paise: 289500, ltp_inr: 2895, current_value_inr: 434250, pnl_inr: 74250, pnl_pct: 20.63, lots_count: 2 },
  { id: "mock-2", security_id: "s2", isin: "INE467B01029", symbol: "TATAELXSI", name: "Tata Elxsi", sector: "IT", quantity: 50, avg_cost_paise: 680000, ltp_paise: 720000, ltp_inr: 7200, current_value_inr: 360000, pnl_inr: 20000, pnl_pct: 5.88, lots_count: 1 },
  { id: "mock-3", security_id: "s3", isin: "INE040A01034", symbol: "HDFCBANK", name: "HDFC Bank", sector: "Banking", quantity: 200, avg_cost_paise: 155000, ltp_paise: 172500, ltp_inr: 1725, current_value_inr: 345000, pnl_inr: 35000, pnl_pct: 11.29, lots_count: 3 },
  { id: "mock-4", security_id: "s4", isin: "INE009A01021", symbol: "INFY", name: "Infosys", sector: "IT", quantity: 100, avg_cost_paise: 145000, ltp_paise: 138000, ltp_inr: 1380, current_value_inr: 138000, pnl_inr: -7000, pnl_pct: -4.83, lots_count: 1 },
  { id: "mock-5", security_id: "s5", isin: "INE585B01010", symbol: "MARUTI", name: "Maruti Suzuki", sector: "Auto", quantity: 20, avg_cost_paise: 1050000, ltp_paise: 1185000, ltp_inr: 11850, current_value_inr: 237000, pnl_inr: 27000, pnl_pct: 12.86, lots_count: 1 },
  { id: "mock-6", security_id: "s6", isin: "INE154A01025", symbol: "ITC", name: "ITC Ltd", sector: "FMCG", quantity: 500, avg_cost_paise: 43000, ltp_paise: 47500, ltp_inr: 475, current_value_inr: 237500, pnl_inr: 22500, pnl_pct: 10.47, lots_count: 2 },
  { id: "mock-7", security_id: "s7", isin: "INE021A01026", symbol: "CIPLA", name: "Cipla", sector: "Pharma", quantity: 80, avg_cost_paise: 120000, ltp_paise: 132500, ltp_inr: 1325, current_value_inr: 106000, pnl_inr: 10000, pnl_pct: 10.42, lots_count: 1 },
  { id: "mock-8", security_id: "s8", isin: "INE114A01011", symbol: "SUNPHARMA", name: "Sun Pharma", sector: "Pharma", quantity: 120, avg_cost_paise: 105000, ltp_paise: 115500, ltp_inr: 1155, current_value_inr: 138600, pnl_inr: 12600, pnl_pct: 10.0, lots_count: 1 },
];

// ── Pie chart colors ──────────────────────────────────────────────────────
const SECTOR_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
];

function SectorPieChart({ holdings }: { holdings: Holding[] }) {
  const sectorData = useMemo(() => {
    const map: Record<string, number> = {};
    for (const h of holdings) {
      const sec = h.sector || "Other";
      const val = h.current_value_inr ?? (h.avg_cost_paise * h.quantity) / 100;
      map[sec] = (map[sec] || 0) + val;
    }
    const total = Object.values(map).reduce((a, b) => a + b, 0);
    return Object.entries(map)
      .sort((a, b) => b[1] - a[1])
      .map(([sector, value], i) => ({
        sector,
        value,
        pct: total > 0 ? (value / total) * 100 : 0,
        color: SECTOR_COLORS[i % SECTOR_COLORS.length],
      }));
  }, [holdings]);

  if (sectorData.length === 0) return null;

  // Build SVG pie chart
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const r = 80;

  let cumAngle = -90;
  const slices = sectorData.map((d) => {
    const angle = (d.pct / 100) * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const endAngle = cumAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const largeArc = angle > 180 ? 1 : 0;

    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);

    const path =
      sectorData.length === 1
        ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} Z`
        : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;

    return { ...d, path };
  });

  return (
    <Card style={{ marginTop: 20 }}>
      <h2 style={{ marginBottom: 16 }}>Sector Allocation</h2>
      <div style={{ display: "flex", alignItems: "center", gap: 32, flexWrap: "wrap" }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {slices.map((s, i) => (
            <path key={i} d={s.path} fill={s.color} stroke="var(--bg-card, #fff)" strokeWidth={2} />
          ))}
        </svg>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {sectorData.map((d, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".9rem" }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: d.color, flexShrink: 0 }} />
              <span style={{ fontWeight: 500 }}>{d.sector}</span>
              <span className="muted">{d.pct.toFixed(1)}%</span>
              <span className="muted">({inrVal(d.value)})</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── New Account Form ──────────────────────────────────────────────────────
function NewAccountForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const { data: clients = [] } = useQuery({ queryKey: ["clients"], queryFn: clientsApi.list });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const [clientId, setClientId] = useState("");
  const [strategyId, setStrategyId] = useState("");
  const [accountCode, setAccountCode] = useState("");
  const [inceptionDate, setInceptionDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      portfolioApi.createAccount({
        client_id: clientId,
        strategy_id: strategyId,
        account_code: accountCode,
        inception_date: inceptionDate,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = clientId && strategyId && accountCode.trim() && inceptionDate;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>New Portfolio Account</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>

      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Client</label>
          <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">— Select client —</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.full_name} ({c.client_code})</option>)}
          </select>
        </div>
        <div>
          <label className="label">Strategy</label>
          <select className="input" value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
            <option value="">— Select strategy —</option>
            {strategies.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Account Code</label>
          <input className="input" value={accountCode} onChange={(e) => setAccountCode(e.target.value.toUpperCase())} placeholder="e.g. PMS-001-LCV" />
        </div>
        <div>
          <label className="label">Inception Date</label>
          <input className="input" type="date" value={inceptionDate} onChange={(e) => setInceptionDate(e.target.value)} />
        </div>
      </div>

      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Create Account
      </Button>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────
export function HoldingsPage() {
  const qc = useQueryClient();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showMock, setShowMock] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);

  const { data: accounts = [], isLoading: loadingAccounts } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.accounts(),
  });

  const { data: apiHoldings = [], isLoading: loadingHoldings } = useQuery({
    queryKey: ["holdings", selectedAccount],
    queryFn: () => (selectedAccount ? portfolioApi.holdings(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  // Use mock data when no real holdings exist and user toggles demo mode
  const holdings = (selectedAccount && apiHoldings.length === 0 && showMock) ? MOCK_HOLDINGS : apiHoldings;

  // Computed totals
  const totalCost = holdings.reduce((sum, h) => sum + h.avg_cost_paise * h.quantity, 0);
  const totalCurrentValue = holdings.reduce((sum, h) => sum + (h.current_value_inr ?? (h.avg_cost_paise * h.quantity) / 100), 0);
  const totalPnl = holdings.reduce((sum, h) => sum + (h.pnl_inr ?? 0), 0);
  const totalPnlPct = totalCost > 0 ? (totalPnl / (totalCost / 100)) * 100 : 0;

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Portfolio Holdings</h1>
          <p className="muted">View holdings by portfolio account</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!showForm && <Button variant="primary" onClick={() => setShowForm(true)}>+ New Account</Button>}
        </div>
      </div>

      {showForm && (
        <NewAccountForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Portfolio account created.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["portfolio-accounts"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi"><span className="kpi__value">{accounts.length}</span><span className="kpi__label">Portfolio accounts</span></div>
        <div className="kpi"><span className="kpi__value">{holdings.length}</span><span className="kpi__label">Positions</span></div>
        {holdings.length > 0 && (
          <>
            <div className="kpi"><span className="kpi__value">{inrVal(totalCurrentValue)}</span><span className="kpi__label">Current Value</span></div>
            <div className="kpi">
              <span className="kpi__value" style={{ color: totalPnl >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)" }}>
                {totalPnl >= 0 ? "+" : ""}{inrVal(totalPnl)} ({totalPnlPct >= 0 ? "+" : ""}{totalPnlPct.toFixed(2)}%)
              </span>
              <span className="kpi__label">Unrealized P&L</span>
            </div>
          </>
        )}
      </div>

      <Card>
        <h2 style={{ marginBottom: 16 }}>Accounts</h2>
        {loadingAccounts ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : accounts.length === 0 ? (
          <div className="empty">No portfolio accounts yet. Create one after onboarding a client.</div>
        ) : (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
            {accounts.map((a: PortfolioAccount) => (
              <button key={a.id} className={`btn ${selectedAccount === a.id ? "btn--primary" : "btn--ghost"}`} onClick={() => setSelectedAccount(a.id)}>
                {a.account_code}
                <span className="faint" style={{ marginLeft: 6, fontSize: ".8rem" }}>{stratMap[a.strategy_id] || ""}</span>
              </button>
            ))}
          </div>
        )}
      </Card>

      {selectedAccount && (
        <Card style={{ marginTop: 20 }}>
          <div className="row row--between" style={{ marginBottom: 16 }}>
            <h2>
              Holdings — {accounts.find((a: PortfolioAccount) => a.id === selectedAccount)?.account_code}
            </h2>
            {apiHoldings.length === 0 && (
              <Button variant="ghost" onClick={() => setShowMock(!showMock)}>
                {showMock ? "Hide Demo Data" : "Show Demo Data"}
              </Button>
            )}
          </div>
          {loadingHoldings ? (
            <div className="empty"><span className="spinner" /> Loading...</div>
          ) : holdings.length === 0 ? (
            <div className="empty">
              No holdings in this account.
              <br />
              <button className="link" style={{ marginTop: 8, fontSize: ".9rem", cursor: "pointer", background: "none", border: "none", color: "var(--primary)", textDecoration: "underline" }} onClick={() => setShowMock(true)}>
                Load demo data to preview
              </button>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Security</th>
                    <th>Sector</th>
                    <th style={{ textAlign: "right" }}>Qty</th>
                    <th style={{ textAlign: "right" }}>Avg Cost</th>
                    <th style={{ textAlign: "right" }}>LTP</th>
                    <th style={{ textAlign: "right" }}>Cost Value</th>
                    <th style={{ textAlign: "right" }}>Current Value</th>
                    <th style={{ textAlign: "right" }}>P&L</th>
                    <th style={{ textAlign: "right" }}>P&L %</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h: Holding) => {
                    const costValue = h.avg_cost_paise * h.quantity;
                    const currentValue = h.current_value_inr ?? costValue / 100;
                    const pnl = h.pnl_inr ?? 0;
                    const pnlPct = h.pnl_pct ?? 0;
                    const isPositive = pnl >= 0;

                    return (
                      <tr key={h.id}>
                        <td className="mono" style={{ fontWeight: 600 }}>{h.symbol || h.security_id.slice(0, 8)}</td>
                        <td>{h.sector || "—"}</td>
                        <td style={{ textAlign: "right" }}>{h.quantity}</td>
                        <td style={{ textAlign: "right" }}>{inr(h.avg_cost_paise)}</td>
                        <td style={{ textAlign: "right" }}>{h.ltp_paise ? inr(h.ltp_paise) : "—"}</td>
                        <td style={{ textAlign: "right" }}>{inr(costValue)}</td>
                        <td style={{ textAlign: "right" }}>{inrVal(currentValue)}</td>
                        <td style={{ textAlign: "right", color: isPositive ? "var(--success, #10b981)" : "var(--danger, #ef4444)", fontWeight: 600 }}>
                          {isPositive ? "+" : ""}{inrVal(pnl)}
                        </td>
                        <td style={{ textAlign: "right", color: isPositive ? "var(--success, #10b981)" : "var(--danger, #ef4444)", fontWeight: 600 }}>
                          {isPositive ? "+" : ""}{pnlPct.toFixed(2)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 700, borderTop: "2px solid var(--border, #e5e7eb)" }}>
                    <td colSpan={5}>Total</td>
                    <td style={{ textAlign: "right" }}>{inr(totalCost)}</td>
                    <td style={{ textAlign: "right" }}>{inrVal(totalCurrentValue)}</td>
                    <td style={{ textAlign: "right", color: totalPnl >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)" }}>
                      {totalPnl >= 0 ? "+" : ""}{inrVal(totalPnl)}
                    </td>
                    <td style={{ textAlign: "right", color: totalPnlPct >= 0 ? "var(--success, #10b981)" : "var(--danger, #ef4444)" }}>
                      {totalPnlPct >= 0 ? "+" : ""}{totalPnlPct.toFixed(2)}%
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Sector Allocation Chart */}
      {holdings.length > 0 && <SectorPieChart holdings={holdings} />}

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </div>
  );
}
