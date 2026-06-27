import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, Activity } from "./api";
import { dashboardApi } from "../dashboard/api";
import { Card, Button, KPI, SkeletonTable, SkeletonKPIs, useToast } from "../../components/ui";

const ENTITY_FILTERS = ["all", "application", "order", "trade", "client", "portfolio", "system"];

const ACTION_ICONS: Record<string, string> = {
  created: "✦", approved: "✓", rejected: "✕", submitted: "▤",
  filled: "⬡", settled: "⇄", updated: "◈", provisioned: "❖", login: "◉",
};

const SAMPLE_ACTIVITIES: Omit<Activity, "id">[] = [
  // ── application ──
  { actor_role: "compliance", actor_subject: "Aarii Parekh", action: "approved", entity_type: "application", entity_id: "a1b2c3d4", detail: "Rohan Iyer onboarding approved — client provisioned as CL-ECD32520", is_read: false, created_at: new Date(Date.now() - 900000).toISOString() },
  { actor_role: "compliance", actor_subject: "Kavita Deshmukh", action: "approved", entity_type: "application", entity_id: "e5f6a7b8", detail: "Neha Kapoor onboarding approved — investment ₹2.50 Cr, risk: Aggressive", is_read: false, created_at: new Date(Date.now() - 1800000).toISOString() },
  { actor_role: "relationship_manager", actor_subject: "Sanjay Gupta", action: "submitted", entity_type: "application", entity_id: "f3a4b5c6", detail: "Arjun Nair application submitted for compliance review — ₹75L individual", is_read: true, created_at: new Date(Date.now() - 5400000).toISOString() },
  { actor_role: "relationship_manager", actor_subject: "Sanjay Gupta", action: "submitted", entity_type: "application", entity_id: "d7e8f9a0", detail: "Priya Sharma application submitted — ₹1.50 Cr, aggressive risk profile", is_read: true, created_at: new Date(Date.now() - 7200000).toISOString() },
  { actor_role: "system", actor_subject: "KYC Gateway", action: "updated", entity_type: "application", entity_id: "b1c2d3e4", detail: "KYC verification completed for Meera Joshi via CKYC — PAN & Aadhaar validated", is_read: true, created_at: new Date(Date.now() - 10800000).toISOString() },
  { actor_role: "compliance", actor_subject: "Aarii Parekh", action: "rejected", entity_type: "application", entity_id: "c7d8e9f0", detail: "Application rejected — incomplete bank verification documents", is_read: true, created_at: new Date(Date.now() - 64800000).toISOString() },

  // ── order ──
  { actor_role: "relationship_manager", actor_subject: "Sanjay Gupta", action: "created", entity_type: "order", entity_id: "ORD-20260627", detail: "Buy 500 RELIANCE @ ₹2,845.60 for Rohan Iyer — market order", is_read: false, created_at: new Date(Date.now() - 2700000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "filled", entity_type: "order", entity_id: "ORD-20260626", detail: "Buy 200 TCS @ ₹4,120.00 executed — filled 200/200 shares", is_read: true, created_at: new Date(Date.now() - 14400000).toISOString() },
  { actor_role: "relationship_manager", actor_subject: "Sanjay Gupta", action: "created", entity_type: "order", entity_id: "ORD-20260625", detail: "Sell 100 INFY @ ₹1,590.25 for Neha Kapoor — limit order", is_read: true, created_at: new Date(Date.now() - 36000000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "filled", entity_type: "order", entity_id: "ORD-20260624", detail: "Buy 1000 HDFCBANK @ ₹1,712.40 executed — partial fill 800/1000", is_read: true, created_at: new Date(Date.now() - 57600000).toISOString() },

  // ── trade ──
  { actor_role: "system", actor_subject: "NSE Gateway", action: "settled", entity_type: "trade", entity_id: "TRD-78254", detail: "RELIANCE buy 500 shares settled T+1 — ₹14,22,800 debited from Rohan Iyer", is_read: false, created_at: new Date(Date.now() - 3600000).toISOString() },
  { actor_role: "system", actor_subject: "NSE Gateway", action: "settled", entity_type: "trade", entity_id: "TRD-78190", detail: "TCS buy 200 shares settled — ₹8,24,000 debited from Vikram Mehta", is_read: true, created_at: new Date(Date.now() - 18000000).toISOString() },
  { actor_role: "system", actor_subject: "BSE Gateway", action: "settled", entity_type: "trade", entity_id: "TRD-78120", detail: "ICICIBANK sell 300 shares settled — ₹3,69,900 credited to Asha Rao", is_read: true, created_at: new Date(Date.now() - 43200000).toISOString() },

  // ── client ──
  { actor_role: "system", actor_subject: "Aurum PMS", action: "provisioned", entity_type: "client", entity_id: "c9d0e1f2", detail: "Client account created for Vikram Mehta — PAN verified, bank linked", is_read: false, created_at: new Date(Date.now() - 4500000).toISOString() },
  { actor_role: "compliance", actor_subject: "Kavita Deshmukh", action: "updated", entity_type: "client", entity_id: "d1e2f3a4", detail: "Neha Kapoor risk profile reassessed — Aggressive → Moderate (quarterly review)", is_read: true, created_at: new Date(Date.now() - 21600000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "provisioned", entity_type: "client", entity_id: "e5f6a7b8", detail: "Client account created for Asha Rao — CL-537B1A50, conservative profile", is_read: true, created_at: new Date(Date.now() - 50400000).toISOString() },

  // ── portfolio ──
  { actor_role: "system", actor_subject: "Aurum PMS", action: "created", entity_type: "portfolio", entity_id: "PF-001", detail: "Portfolio account opened for Rohan Iyer — strategy: Balanced Growth", is_read: true, created_at: new Date(Date.now() - 25200000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "updated", entity_type: "portfolio", entity_id: "PF-002", detail: "Neha Kapoor portfolio rebalanced — 60% equity, 30% debt, 10% gold", is_read: true, created_at: new Date(Date.now() - 28800000).toISOString() },
  { actor_role: "relationship_manager", actor_subject: "Sanjay Gupta", action: "created", entity_type: "portfolio", entity_id: "PF-003", detail: "New portfolio account opened for Vikram Mehta — strategy: Large Cap Focus", is_read: true, created_at: new Date(Date.now() - 54000000).toISOString() },

  // ── system ──
  { actor_role: "system", actor_subject: "Aurum PMS", action: "login", entity_type: "system", entity_id: null, detail: "Admin login from 103.xx.xx.42 — session started", is_read: true, created_at: new Date(Date.now() - 32400000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "updated", entity_type: "system", entity_id: null, detail: "SEBI compliance rules engine updated to v2.1 — minimum investment ₹50L", is_read: true, created_at: new Date(Date.now() - 86400000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "updated", entity_type: "system", entity_id: null, detail: "Daily NAV computation completed — 5 portfolios recalculated", is_read: true, created_at: new Date(Date.now() - 72000000).toISOString() },
];

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  const days = Math.floor(hrs / 24);
  if (days < 30) return days + "d ago";
  return new Date(isoDate).toLocaleDateString("en-IN");
}

export function ActivityFeedPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [showSample, setShowSample] = useState(true);
  const limit = 30;

  const { data, isLoading } = useQuery({
    queryKey: ["activity-feed", filter, page],
    queryFn: () => notificationsApi.feed(filter === "all" ? undefined : filter, limit, page * limit),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success("All marked as read.");
      qc.invalidateQueries({ queryKey: ["activity-feed"] });
      qc.invalidateQueries({ queryKey: ["unread-count"] });
    },
  });

  const markOne = useMutation({
    mutationFn: (id: string) => notificationsApi.markOneRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["activity-feed"] });
      qc.invalidateQueries({ queryKey: ["unread-count"] });
    },
  });

  const items = data?.items || [];
  const total = data?.total || 0;
  const unread = data?.unread || 0;
  const totalPages = Math.ceil(total / limit);
  const isEmpty = !isLoading && items.length === 0;

  const renderActivityItem = (a: Activity | Omit<Activity, "id">, index: number) => {
    const id = "id" in a ? a.id : `sample-${index}`;
    const icon = Object.entries(ACTION_ICONS).find(([k]) => a.action.toLowerCase().includes(k))?.[1] || "•";
    return (
      <div
        key={id}
        style={{
          display: "grid", gridTemplateColumns: "40px 1fr auto", gap: 12,
          padding: "16px 8px", borderBottom: "1px solid var(--line)",
          background: a.is_read ? "transparent" : "rgba(212,175,55,.04)",
          cursor: a.is_read || !("id" in a) ? "default" : "pointer", alignItems: "start",
        }}
        onClick={() => { if ("id" in a && !a.is_read) markOne.mutate(a.id); }}
      >
        <div style={{
          width: 36, height: 36, borderRadius: "50%", display: "grid", placeItems: "center",
          background: a.is_read ? "var(--glass)" : "var(--gold-dim)",
          border: "1px solid " + (a.is_read ? "var(--line)" : "var(--glass-border)"),
          fontSize: "1rem",
        }}>
          {icon}
        </div>
        <div>
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontWeight: 600 }}>{a.actor_subject}</span>
            <span className="muted" style={{ marginLeft: 6, fontSize: ".85rem" }}>({a.actor_role})</span>
          </div>
          <div style={{ fontSize: ".92rem" }}>
            <span style={{ color: "var(--gold-2)" }}>{a.action}</span>
            <span className="muted"> on </span>
            <span style={{ fontWeight: 500 }}>{a.entity_type}</span>
            {a.entity_id && <span className="mono" style={{ marginLeft: 6, fontSize: ".78rem" }}>{a.entity_id.slice(0, 8)}</span>}
          </div>
          {a.detail && <div className="muted" style={{ fontSize: ".82rem", marginTop: 4 }}>{a.detail}</div>}
        </div>
        <div style={{ fontSize: ".78rem", color: "var(--faint)", whiteSpace: "nowrap" }}>
          {timeAgo(a.created_at)}
          {!a.is_read && <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--gold)", marginLeft: 8, verticalAlign: "middle" }} />}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Activity Feed</h1>
          <p className="muted">Real-time log of all platform activity</p>
        </div>
        {unread > 0 && (
          <Button variant="ghost" loading={markAll.isPending} onClick={() => markAll.mutate()}>
            Mark all read ({unread})
          </Button>
        )}
      </div>

      {/* ── System Stats ── */}
      {statsLoading ? (
        <SkeletonKPIs count={4} />
      ) : stats ? (
        <div className="kpis" style={{ marginBottom: 24 }}>
          <KPI
            value={
              <span style={{ fontSize: "1.2rem" }}>
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
              stats.pending_review > 0 ? (
                <span style={{ color: "var(--warning)" }}>{stats.pending_review}</span>
              ) : "0"
            }
            label="Pending review"
          />
        </div>
      ) : null}

      {/* ── Quick Actions ── */}
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", marginBottom: 24, gap: 12 }}>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }}
          onClick={() => navigate("/onboarding")}
        >
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>✦</div>
          <div style={{ fontWeight: 600, fontSize: ".9rem" }}>New Onboarding</div>
          <div className="faint" style={{ fontSize: ".78rem", marginTop: 4 }}>Start client application</div>
        </Card>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }}
          onClick={() => navigate("/review")}
        >
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>▤</div>
          <div style={{ fontWeight: 600, fontSize: ".9rem" }}>Review Queue</div>
          <div className="faint" style={{ fontSize: ".78rem", marginTop: 4 }}>Pending applications</div>
        </Card>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }}
          onClick={() => navigate("/clients")}
        >
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>❖</div>
          <div style={{ fontWeight: 600, fontSize: ".9rem" }}>Clients</div>
          <div className="faint" style={{ fontSize: ".78rem", marginTop: 4 }}>Client directory</div>
        </Card>
        <Card
          glass
          className="quick-action"
          style={{ cursor: "pointer", textAlign: "center", padding: "20px 12px" }}
          onClick={() => navigate("/trading")}
        >
          <div style={{ fontSize: "1.4rem", marginBottom: 6 }}>⇄</div>
          <div style={{ fontWeight: 600, fontSize: ".9rem" }}>Order Book</div>
          <div className="faint" style={{ fontSize: ".78rem", marginTop: 4 }}>Trading & orders</div>
        </Card>
      </div>

      {/* ── Activity KPIs ── */}
      {isLoading ? (
        <SkeletonKPIs count={2} />
      ) : (() => {
        const sampleFiltered = SAMPLE_ACTIVITIES.filter((a) => filter === "all" || a.entity_type === filter);
        const displayTotal = total || (isEmpty && showSample ? sampleFiltered.length : 0);
        const displayUnread = unread || (isEmpty && showSample ? sampleFiltered.filter((a) => !a.is_read).length : 0);
        return (
          <div className="kpis" style={{ marginBottom: 20 }}>
            <div className="kpi"><span className="kpi__value">{displayTotal}</span><span className="kpi__label">Total events</span></div>
            <div className="kpi"><span className="kpi__value" style={{ color: displayUnread > 0 ? "var(--warning)" : undefined }}>{displayUnread}</span><span className="kpi__label">Unread</span></div>
          </div>
        );
      })()}

      {/* ── Filter Chips ── */}
      <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {ENTITY_FILTERS.map((f) => (
          <button key={f} className={`btn btn--sm ${filter === f ? "btn--primary" : "btn--ghost"}`} onClick={() => { setFilter(f); setPage(0); }}>
            {f}
          </button>
        ))}
      </div>

      {/* ── Activity List ── */}
      <Card>
        {isLoading ? (
          <SkeletonTable rows={8} cols={3} />
        ) : isEmpty && !showSample ? (
          <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: 12, opacity: 0.3 }}>◉</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 500, marginBottom: 8 }}>No activity recorded yet</div>
            <p className="muted" style={{ marginBottom: 20, maxWidth: 400, margin: "0 auto 20px" }}>
              Activity events will appear here as you onboard clients, process applications, execute trades, and manage portfolios.
            </p>
            <Button variant="primary" onClick={() => setShowSample(true)}>
              Show sample activity
            </Button>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 0 }}>
            {isEmpty && showSample ? (
              <>
                {SAMPLE_ACTIVITIES
                  .filter((a) => filter === "all" || a.entity_type === filter)
                  .map((a, i) => renderActivityItem(a, i))}
              </>
            ) : (
              items.map((a: Activity, i: number) => renderActivityItem(a, i))
            )}
          </div>
        )}

        {totalPages > 1 && (
          <div className="row row--between" style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--line)" }}>
            <Button variant="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>&larr; Newer</Button>
            <span className="muted">Page {page + 1} of {totalPages}</span>
            <Button variant="ghost" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Older &rarr;</Button>
          </div>
        )}
      </Card>
    </div>
  );
}
