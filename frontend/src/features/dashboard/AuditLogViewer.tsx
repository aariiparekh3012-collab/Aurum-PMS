import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { Card, StatusBadge, SkeletonTable } from "../../components/ui";

interface AuditLogEntry {
  id: string;
  event_type: string;
  description: string;
  actor_id: string | null;
  actor_role: string | null;
  actor_email: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

interface AuditLogPage {
  logs: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

const EVENT_TYPE_OPTIONS = [
  { label: "All", value: "" },
  { label: "Auth", value: "auth" },
  { label: "Onboarding", value: "onboarding" },
  { label: "Orders", value: "order" },
  { label: "Trades", value: "trade" },
];

const eventColor = (type: string): string => {
  if (type.startsWith("auth")) return "var(--info)";
  if (type.startsWith("onboarding")) return "var(--warning)";
  if (type.startsWith("order")) return "var(--primary)";
  if (type.startsWith("trade")) return "var(--success)";
  return "var(--muted)";
};

export function AuditLogViewer() {
  const [eventFilter, setEventFilter] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", eventFilter, page],
    queryFn: () => {
      const params = new URLSearchParams();
      if (eventFilter) params.set("event_type", eventFilter);
      params.set("offset", String(page * pageSize));
      params.set("limit", String(pageSize));
      return apiClient
        .get<AuditLogPage>(`/audit/logs?${params}`)
        .then((r) => r.data);
    },
  });

  return (
    <Card>
      <div
        className="row row--between"
        style={{ marginBottom: 16, flexWrap: "wrap", gap: 12 }}
      >
        <h2>Audit Trail</h2>
        <div className="row" style={{ gap: 8 }}>
          {EVENT_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`btn btn--sm ${eventFilter === opt.value ? "btn--primary" : "btn--ghost"}`}
              onClick={() => {
                setEventFilter(opt.value);
                setPage(0);
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !data ? (
        <SkeletonTable rows={8} cols={5} />
      ) : data.logs.length === 0 ? (
        <div className="empty">No audit entries found.</div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Description</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {data.logs.map((log) => (
                  <tr key={log.id}>
                    <td
                      className="mono"
                      style={{ fontSize: ".78rem", whiteSpace: "nowrap" }}
                    >
                      {new Date(log.created_at).toLocaleString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: ".78rem",
                          fontWeight: 600,
                          background: `color-mix(in srgb, ${eventColor(log.event_type)} 15%, transparent)`,
                          color: eventColor(log.event_type),
                        }}
                      >
                        {log.event_type}
                      </span>
                    </td>
                    <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {log.description}
                    </td>
                    <td>
                      <div style={{ fontSize: ".82rem" }}>
                        {log.actor_email || log.actor_id || "system"}
                      </div>
                      {log.actor_role && (
                        <div className="faint" style={{ fontSize: ".72rem", textTransform: "capitalize" }}>
                          {log.actor_role}
                        </div>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: ".78rem" }}>
                      {log.resource_type && (
                        <>
                          {log.resource_type}
                          {log.resource_id && (
                            <span className="faint">/{log.resource_id.slice(0, 8)}</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: ".75rem", color: "var(--muted)" }}>
                      {log.ip_address || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div
            className="row row--between"
            style={{ marginTop: 16, fontSize: ".85rem" }}
          >
            <span className="faint">
              Showing {data.offset + 1}–{Math.min(data.offset + data.limit, data.total)} of{" "}
              {data.total}
            </span>
            <div className="row" style={{ gap: 8 }}>
              <button
                className="btn btn--sm btn--ghost"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Prev
              </button>
              <button
                className="btn btn--sm btn--ghost"
                disabled={data.offset + data.limit >= data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
