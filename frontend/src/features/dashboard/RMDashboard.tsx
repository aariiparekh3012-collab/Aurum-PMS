import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { auth } from "@/lib/auth";
import { Card, KPI, StatusBadge, SkeletonKPIs, SkeletonTable } from "../../components/ui";
import { DonutChart, palette, type Slice } from "../../components/charts";

interface ClientRow {
  client_id: string;
  client_code: string;
  full_name: string;
  status: string;
  investor_type: string;
  risk_category: string | null;
  portfolio_count: number;
  total_aum_paise: number;
  total_cost_paise: number;
  unrealised_pnl_paise: number;
  cash_paise: number;
  inception_date: string | null;
}

interface StrategyBreakdown {
  strategy_name: string;
  account_count: number;
  total_aum_paise: number;
}

interface RecentActivity {
  kind: string;
  description: string;
  date: string;
}

interface RMDashData {
  total_clients: number;
  active_clients: number;
  total_aum_paise: number;
  total_portfolios: number;
  pending_orders: number;
  pending_review: number;
  clients: ClientRow[];
  strategy_breakdown: StrategyBreakdown[];
  recent_activity: RecentActivity[];
}

const inrCr = (paise: number) => "₹" + (paise / 1e9).toFixed(2) + " Cr";
const inrL = (paise: number) => {
  const abs = Math.abs(paise / 100);
  if (abs >= 1e7) return (paise >= 0 ? "" : "-") + "₹" + (abs / 1e7).toFixed(2) + " Cr";
  if (abs >= 1e5) return (paise >= 0 ? "" : "-") + "₹" + (abs / 1e5).toFixed(2) + " L";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);
};
const pnlColor = (v: number) => (v >= 0 ? "var(--success)" : "var(--danger)");

export function RMDashboard() {
  const navigate = useNavigate();
  const user = auth.getUser();

  const { data, isLoading } = useQuery({
    queryKey: ["rm-dashboard"],
    queryFn: () => apiClient.get<RMDashData>("/dashboard/rm").then((r) => r.data),
  });

  if (isLoading || !data) {
    return (
      <div className="fade-in">
        <h1>Welcome back, <span className="gold">{user?.full_name ?? "RM"}</span></h1>
        <p className="muted">Loading your book&hellip;</p>
        <SkeletonKPIs count={5} />
        <div style={{ marginTop: 24 }}><SkeletonTable rows={6} cols={6} /></div>
      </div>
    );
  }

  const stratData: Slice[] = data.strategy_breakdown.map((s, i) => ({
    label: s.strategy_name,
    value: Math.round(s.total_aum_paise / 100),
    color: palette(i),
  }));

  const topClients = [...data.clients].sort((a, b) => b.total_aum_paise - a.total_aum_paise);

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>
          Welcome back, <span className="gold">{user?.full_name ?? "RM"}</span>
        </h1>
        <p className="muted">Relationship Manager — Client Book Overview</p>
      </div>

      {/* KPIs */}
      <div className="kpis" style={{ marginBottom: 24 }}>
        <KPI
          value={<span style={{ fontSize: "1.3rem" }}>{inrCr(data.total_aum_paise)}</span>}
          label="Total AUM"
        />
        <KPI value={data.total_clients} label="Clients" />
        <KPI value={data.total_portfolios} label="Portfolios" />
        <KPI
          value={data.pending_orders > 0 ? <span style={{ color: "var(--warning)" }}>{data.pending_orders}</span> : "0"}
          label="Pending Orders"
        />
        <KPI
          value={data.pending_review > 0 ? <span style={{ color: "var(--warning)" }}>{data.pending_review}</span> : "0"}
          label="Pending Review"
        />
      </div>

      {/* Charts row */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <Card>
          <h2 className="card__title">AUM by Strategy</h2>
          {stratData.length > 0 ? (
            <DonutChart data={stratData} size={180} />
          ) : (
            <p className="faint">No strategy data yet.</p>
          )}
        </Card>

        <Card>
          <h2 className="card__title">Recent Activity</h2>
          {data.recent_activity.length === 0 ? (
            <p className="faint">No recent activity.</p>
          ) : (
            <div style={{ display: "grid", gap: 10, maxHeight: 280, overflowY: "auto" }}>
              {data.recent_activity.slice(0, 10).map((a, i) => (
                <div key={i} className="row" style={{ gap: 10, alignItems: "start" }}>
                  <span
                    style={{
                      width: 8, height: 8, borderRadius: "50%", marginTop: 6, flexShrink: 0,
                      background: a.kind === "onboarding" ? "var(--info)" : a.kind === "deposit" ? "var(--success)" : palette(2),
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: ".85rem" }}>{a.description}</div>
                    <div className="faint" style={{ fontSize: ".75rem" }}>
                      {new Date(a.date).toLocaleDateString("en-IN")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "24px 16px" }} onClick={() => navigate("/onboarding")}>
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>✦</div>
          <div style={{ fontWeight: 600 }}>New Client</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>Start onboarding</div>
        </Card>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "24px 16px" }} onClick={() => navigate("/orders")}>
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>▤</div>
          <div style={{ fontWeight: 600 }}>Order Book</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>{data.pending_orders} pending</div>
        </Card>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "24px 16px" }} onClick={() => navigate("/review")}>
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>❖</div>
          <div style={{ fontWeight: 600 }}>Review Queue</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>{data.pending_review} awaiting</div>
        </Card>
      </div>

      {/* Client book table */}
      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Client Book</h2>
          <span className="faint">{data.clients.length} clients</span>
        </div>
        {data.clients.length === 0 ? (
          <div className="empty">No clients yet. Start an onboarding to build your book.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Code</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th style={{ textAlign: "right" }}>AUM</th>
                  <th style={{ textAlign: "right" }}>P&L</th>
                  <th style={{ textAlign: "right" }}>Cash</th>
                  <th style={{ textAlign: "center" }}>Portfolios</th>
                </tr>
              </thead>
              <tbody>
                {topClients.map((c) => (
                  <tr key={c.client_id} style={{ cursor: "pointer" }} onClick={() => navigate(`/clients/${c.client_id}`)}>
                    <td>
                      <span style={{ fontWeight: 600 }}>{c.full_name}</span>
                      <div className="faint" style={{ fontSize: ".75rem", textTransform: "capitalize" }}>{c.investor_type}</div>
                    </td>
                    <td className="mono">{c.client_code}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td style={{ textTransform: "capitalize" }}>{c.risk_category ?? "—"}</td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>{inrL(c.total_aum_paise)}</td>
                    <td style={{ textAlign: "right", color: pnlColor(c.unrealised_pnl_paise) }}>
                      {c.unrealised_pnl_paise >= 0 ? "+" : ""}{inrL(c.unrealised_pnl_paise)}
                    </td>
                    <td style={{ textAlign: "right" }}>{inrL(c.cash_paise)}</td>
                    <td style={{ textAlign: "center" }}>{c.portfolio_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
