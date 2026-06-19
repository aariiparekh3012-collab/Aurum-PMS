import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "./api";
import { applicationsApi } from "../applications/api";
import { Card, KPI, StatusBadge, Button, SkeletonKPIs, SkeletonTable } from "../../components/ui";
import { DonutChart, BarChart, palette, type Slice } from "../../components/charts";
import { auth } from "../../lib/auth";

export function DashboardPage() {
  const navigate = useNavigate();
  const user = auth.getUser();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
  });

  const { data: recentApps = [], isLoading: appsLoading } = useQuery({
    queryKey: ["applications", "all"],
    queryFn: () => applicationsApi.list(),
  });

  if (isLoading || !stats) {
    return (
      <div className="fade-in">
        <div style={{ marginBottom: 24 }}>
          <h1>Welcome back</h1>
          <p className="muted">Loading dashboard&hellip;</p>
        </div>
        <SkeletonKPIs count={4} />
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 24, marginTop: 24 }}>
          <Card><SkeletonTable rows={4} cols={2} /></Card>
          <Card><SkeletonTable rows={4} cols={2} /></Card>
        </div>
        <Card><SkeletonTable rows={5} cols={4} /></Card>
      </div>
    );
  }

  const statusData: Slice[] = stats.applications_by_status.map((s, i) => ({
    label: s.status.replace(/_/g, " "),
    value: s.count,
    color: palette(i),
  }));

  const riskData: Slice[] = stats.clients_by_risk.map((r, i) => ({
    label: r.category,
    value: r.count,
    color: palette(i),
  }));

  const recent = recentApps.slice(0, 5);

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>
          Welcome back, <span className="gold">{user?.full_name ?? user?.subject ?? "User"}</span>
        </h1>
        <p className="muted">Aurum PMS — Platform overview</p>
      </div>

      {/* KPI row */}
      <div className="kpis" style={{ marginBottom: 24 }}>
        <KPI
          value={
            <span style={{ fontSize: "1.35rem" }}>
              {stats.total_aum_paise != null
                ? "₹" + (stats.total_aum_paise / 1e9).toFixed(2) + " Cr"
                : "—"}
            </span>
          }
          label="Total AUM"
        />
        <KPI value={stats.total_clients} label="Clients" />
        <KPI value={stats.total_portfolio_accounts ?? 0} label="Portfolios" />
        <KPI
          value={
            stats.pending_orders > 0 ? (
              <span style={{ color: "var(--warning)" }}>{stats.pending_orders}</span>
            ) : (
              "0"
            )
          }
          label="Orders pending"
        />
        <KPI
          value={
            stats.pending_review > 0 ? (
              <span style={{ color: "var(--warning)" }}>{stats.pending_review}</span>
            ) : (
              "0"
            )
          }
          label="Pending review"
        />
      </div>

      {/* Charts row */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 24 }}>
        <Card>
          <h2 className="card__title">Application status</h2>
          {statusData.length ? (
            <DonutChart data={statusData} />
          ) : (
            <p className="faint">No applications yet.</p>
          )}
        </Card>
        <Card>
          <h2 className="card__title">Client risk profiles</h2>
          {riskData.length ? (
            <BarChart data={riskData} />
          ) : (
            <p className="faint">No risk data yet.</p>
          )}
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", marginBottom: 24 }}>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "28px 16px" }}
          onClick={() => navigate("/onboarding")}
        >
          <div style={{ fontSize: "1.6rem", marginBottom: 8 }}>✦</div>
          <div style={{ fontWeight: 600 }}>New Onboarding</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>
            Start a client application
          </div>
        </Card>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "28px 16px" }}
          onClick={() => navigate("/applications")}
        >
          <div style={{ fontSize: "1.6rem", marginBottom: 8 }}>▤</div>
          <div style={{ fontWeight: 600 }}>Review Queue</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>
            {stats.pending_review} awaiting decision
          </div>
        </Card>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "28px 16px" }}
          onClick={() => navigate("/clients")}
        >
          <div style={{ fontSize: "1.6rem", marginBottom: 8 }}>❖</div>
          <div style={{ fontWeight: 600 }}>Client Directory</div>
          <div className="faint" style={{ fontSize: ".82rem", marginTop: 4 }}>
            {stats.total_clients} onboarded
          </div>
        </Card>
      </div>

      {/* Recent applications table */}
      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Recent applications</h2>
          <Button variant="ghost" onClick={() => navigate("/applications")}>
            View all
          </Button>
        </div>
        {appsLoading ? (
          <SkeletonTable rows={5} cols={4} />
        ) : recent.length === 0 ? (
          <p className="empty">No applications yet. Start an onboarding to see them here.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Type</th>
                <th>Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((a) => (
                <tr key={a.id} onClick={() => navigate("/applications")} style={{ cursor: "pointer" }}>
                  <td>
                    {a.full_name}
                    <div className="faint" style={{ fontSize: ".78rem" }}>{a.email}</div>
                  </td>
                  <td style={{ textTransform: "capitalize" }}>{a.investor_type}</td>
                  <td style={{ textTransform: "capitalize" }}>{a.risk_category ?? "—"}</td>
                  <td><StatusBadge status={a.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
