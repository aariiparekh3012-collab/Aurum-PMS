import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, Activity } from "./api";
import { Card, Button, SkeletonTable, SkeletonKPIs, useToast } from "../../components/ui";

const ENTITY_FILTERS = ["all", "application", "order", "trade", "client", "portfolio", "system"];

const ACTION_ICONS: Record<string, string> = {
  created: "✦", approved: "✓", rejected: "✕", submitted: "▤",
  filled: "⬡", settled: "⇄", updated: "◈", provisioned: "❖", login: "◉",
};

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
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);
  const limit = 30;

  const { data, isLoading } = useQuery({
    queryKey: ["activity-feed", filter, page],
    queryFn: () => notificationsApi.feed(filter === "all" ? undefined : filter, limit, page * limit),
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

      {isLoading ? (
        <SkeletonKPIs count={2} />
      ) : (
        <div className="kpis" style={{ marginBottom: 20 }}>
          <div className="kpi"><span className="kpi__value">{total}</span><span className="kpi__label">Total events</span></div>
          <div className="kpi"><span className="kpi__value" style={{ color: unread > 0 ? "var(--warning)" : undefined }}>{unread}</span><span className="kpi__label">Unread</span></div>
        </div>
      )}

      <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {ENTITY_FILTERS.map((f) => (
          <button key={f} className={`btn btn--sm ${filter === f ? "btn--primary" : "btn--ghost"}`} onClick={() => { setFilter(f); setPage(0); }}>
            {f}
          </button>
        ))}
      </div>

      <Card>
        {isLoading ? (
          <SkeletonTable rows={8} cols={3} />
        ) : items.length === 0 ? (
          <div className="empty">No activity recorded yet.</div>
        ) : (
          <div style={{ display: "grid", gap: 0 }}>
            {items.map((a: Activity) => {
              const icon = Object.entries(ACTION_ICONS).find(([k]) => a.action.toLowerCase().includes(k))?.[1] || "•";
              return (
                <div
                  key={a.id}
                  style={{
                    display: "grid", gridTemplateColumns: "40px 1fr auto", gap: 12,
                    padding: "16px 8px", borderBottom: "1px solid var(--line)",
                    background: a.is_read ? "transparent" : "rgba(212,175,55,.04)",
                    cursor: a.is_read ? "default" : "pointer", alignItems: "start",
                  }}
                  onClick={() => { if (!a.is_read) markOne.mutate(a.id); }}
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
            })}
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
