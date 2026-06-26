import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { auth } from "@/lib/auth";
import { Card, KPI, StatusBadge, SkeletonKPIs, SkeletonTable } from "../../components/ui";
import { DonutChart, BarChart, palette, type Slice } from "../../components/charts";
import { AuditLogViewer } from "./AuditLogViewer";

interface StatusCount { status: string; count: number; }
interface RiskCount { category: string; count: number; }

interface OnboardingPipelineItem {
  id: string;
  full_name: string;
  status: string;
  investor_type: string;
  proposed_investment_inr: number;
  created_at: string;
  risk_category: string | null;
}

interface FeeCollectionSummary {
  total_mgmt_fees_paise: number;
  total_perf_fees_paise: number;
  total_exit_load_paise: number;
  total_fees_paise: number;
}

interface ComplianceData {
  total_clients: number;
  active_clients: number;
  total_aum_paise: number;
  total_portfolios: number;
  pending_review: number;
  pending_orders: number;
  onboarding_pipeline: OnboardingPipelineItem[];
  fee_summary: FeeCollectionSummary;
  applications_by_status: StatusCount[];
  clients_by_risk: RiskCount[];
  accounts_without_fee_schedule: number;
}

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

const inrCr = (paise: number) => "₹" + (paise / 1e9).toFixed(2) + " Cr";

export function ComplianceDashboard() {
  const navigate = useNavigate();
  const user = auth.getUser();

  const { data, isLoading } = useQuery({
    queryKey: ["compliance-dashboard"],
    queryFn: () => apiClient.get<ComplianceData>("/dashboard/compliance").then((r) => r.data),
  });

  if (isLoading || !data) {
    return (
      <div className="fade-in">
        <h1>Compliance Dashboard</h1>
        <p className="muted">Loading&hellip;</p>
        <SkeletonKPIs count={5} />
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 24 }}>
          <Card><SkeletonTable rows={4} cols={3} /></Card>
          <Card><SkeletonTable rows={4} cols={3} /></Card>
        </div>
      </div>
    );
  }

  const statusData: Slice[] = data.applications_by_status.map((s, i) => ({
    label: s.status.replace(/_/g, " "),
    value: s.count,
    color: palette(i),
  }));

  const riskData: Slice[] = data.clients_by_risk.map((r, i) => ({
    label: r.category,
    value: r.count,
    color: palette(i),
  }));

  const feeData: Slice[] = [
    { label: "Management", value: data.fee_summary.total_mgmt_fees_paise, color: palette(0) },
    { label: "Performance", value: data.fee_summary.total_perf_fees_paise, color: palette(1) },
    { label: "Exit Load", value: data.fee_summary.total_exit_load_paise, color: palette(2) },
  ].filter((s) => s.value > 0);

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>
          Compliance Dashboard
        </h1>
        <p className="muted">Regulatory overview — {user?.full_name ?? "Compliance Officer"}</p>
      </div>

      {/* KPI row */}
      <div className="kpis" style={{ marginBottom: 24 }}>
        <KPI
          value={<span style={{ fontSize: "1.3rem" }}>{inrCr(data.total_aum_paise)}</span>}
          label="Total AUM"
        />
        <KPI value={data.active_clients} label={`Active / ${data.total_clients} Clients`} />
        <KPI value={data.total_portfolios} label="Portfolios" />
        <KPI
          value={
            data.pending_review > 0
              ? <span style={{ color: "var(--warning)" }}>{data.pending_review}</span>
              : "0"
          }
          label="Pending Review"
        />
        <KPI
          value={
            data.accounts_without_fee_schedule > 0
              ? <span style={{ color: "var(--danger)" }}>{data.accounts_without_fee_schedule}</span>
              : <span style={{ color: "var(--success)" }}>0</span>
          }
          label="No Fee Schedule"
        />
      </div>

      {/* Alerts */}
      {(data.pending_review > 0 || data.accounts_without_fee_schedule > 0) && (
        <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
          {data.pending_review > 0 && (
            <div
              style={{
                padding: "10px 16px", borderRadius: 8, fontSize: ".88rem", cursor: "pointer",
                background: "var(--warning-bg, rgba(251,191,36,.1))", border: "1px solid var(--warning)",
              }}
              onClick={() => navigate("/review")}
            >
              ⚠ {data.pending_review} application(s) awaiting compliance review
            </div>
          )}
          {data.accounts_without_fee_schedule > 0 && (
            <div
              style={{
                padding: "10px 16px", borderRadius: 8, fontSize: ".88rem", cursor: "pointer",
                background: "rgba(248,113,113,.08)", border: "1px solid var(--danger)",
              }}
              onClick={() => navigate("/fee-schedules")}
            >
              ⚠ {data.accounts_without_fee_schedule} active account(s) without fee schedule assigned
            </div>
          )}
        </div>
      )}

      {/* Charts */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 24, marginBottom: 24 }}>
        <Card>
          <h2 className="card__title">Application Status</h2>
          {statusData.length > 0 ? <DonutChart data={statusData} /> : <p className="faint">No data</p>}
        </Card>
        <Card>
          <h2 className="card__title">Client Risk Profiles</h2>
          {riskData.length > 0 ? <BarChart data={riskData} /> : <p className="faint">No data</p>}
        </Card>
        <Card>
          <h2 className="card__title">Fee Collection</h2>
          {feeData.length > 0 ? (
            <>
              <DonutChart data={feeData.map((d) => ({ ...d, value: Math.round(d.value / 100) }))} size={160} />
              <div style={{ textAlign: "center", marginTop: 8, fontWeight: 600 }}>
                Total: {inr(data.fee_summary.total_fees_paise)}
              </div>
            </>
          ) : (
            <p className="faint">No fees collected yet.</p>
          )}
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }} onClick={() => navigate("/review")}>
          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>❖</div>
          <div style={{ fontWeight: 600, fontSize: ".88rem" }}>Review Queue</div>
        </Card>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }} onClick={() => navigate("/fee-management")}>
          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>💰</div>
          <div style={{ fontWeight: 600, fontSize: ".88rem" }}>Fee Billing</div>
        </Card>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }} onClick={() => navigate("/market-data")}>
          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>📊</div>
          <div style={{ fontWeight: 600, fontSize: ".88rem" }}>Market Data</div>
        </Card>
        <Card glass className="quick-action" style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }} onClick={() => navigate("/clients")}>
          <div style={{ fontSize: "1.3rem", marginBottom: 4 }}>👥</div>
          <div style={{ fontWeight: 600, fontSize: ".88rem" }}>Client Directory</div>
        </Card>
      </div>

      {/* Onboarding pipeline */}
      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Onboarding Pipeline</h2>
          <span className="faint">{data.onboarding_pipeline.length} in progress</span>
        </div>
        {data.onboarding_pipeline.length === 0 ? (
          <div className="empty">All applications have been processed.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Type</th>
                <th>Proposed Investment</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Applied</th>
              </tr>
            </thead>
            <tbody>
              {data.onboarding_pipeline.map((a) => (
                <tr
                  key={a.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/compliance/review/${a.id}`)}
                >
                  <td style={{ fontWeight: 500 }}>{a.full_name}</td>
                  <td style={{ textTransform: "capitalize" }}>{a.investor_type}</td>
                  <td style={{ textAlign: "right" }}>
                    {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(a.proposed_investment_inr)}
                  </td>
                  <td style={{ textTransform: "capitalize" }}>{a.risk_category ?? "—"}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td className="faint" style={{ fontSize: ".82rem" }}>
                    {a.created_at ? new Date(a.created_at).toLocaleDateString("en-IN") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Audit Trail */}
      <div style={{ marginTop: 24 }}>
        <AuditLogViewer />
      </div>
    </div>
  );
}
