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
  { actor_role: "system", actor_subject: "Aurum PMS", action: "Platform deployed", entity_type: "system", entity_id: null, detail: "Production environment is live on Render", is_read: false, created_at: new Date().toISOString() },
  { actor_role: "compliance", actor_subject: "Admin", action: "created", entity_type: "system", entity_id: null, detail: "Initial system configuration completed", is_read: false, created_at: new Date(Date.now() - 60000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "provisioned", entity_type: "system", entity_id: null, detail: "Database migrations applied successfully", is_read: true, created_at: new Date(Date.now() - 120000).toISOString() },
  { actor_role: "system", actor_subject: "Aurum PMS", action: "updated", entity_type: "system", entity_id: null, detail: "Security keys and encryption configured", is_read: true, created_at: new Date(Date.now() - 180000).toISOString() },
  { actor_role: "compliance", actor_subject: "Admin", action: "created", entity_type: "application", entity_id: null, detail: "Onboarding workflow ready for new clients", is_read: true, created_at: new Date(Date.now() - 300000).toISOString() },
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
  const [showSample, setShowSample] = useState(false);
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
      ) : (
        <div className="kpis" style={{ marginBottom: 20 }}>
          <div className="kpi"><span className="kpi__value">{total}</span><span className="kpi__label">Total events</span></div>
          <div className="kpi"><span className="kpi__value" style={{ color: unread > 0 ? "var(--warning)" : undefined }}>{unread}</span><span className="kpi__label">Unread</span></div>
        </div>
      )}

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
                <div style={{ padding: "12px 8px", borderBottom: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: ".82rem", fontStyle: "italic" }}>
                    Sample data — these are placeholder events to preview the feed
                  </span>
                  <Button variant="ghost" onClick={() => setShowSample(false)} style={{ fontSize: ".8rem", padding: "4px 10px" }}>
                    Hide
                  </Button>
                </div>
                {SAMPLE_ACTIVITIES.map((a, i) => renderActivityItem(a, i))}
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
