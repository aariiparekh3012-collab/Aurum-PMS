import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, Button, SkeletonTable } from "../../components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { nseReportsApi, BhavCopyRecord } from "./nseReportsApi";

// ── helpers ────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatSize(bytes: number | null) {
  if (!bytes) return "—";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function formatTs(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function isToday(dateStr: string) {
  return dateStr === new Date().toISOString().slice(0, 10);
}

// ── StatusPill ─────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: BhavCopyRecord["status"] }) {
  const map: Record<string, { label: string; bg: string; color: string }> = {
    downloaded: { label: "Ready",   bg: "var(--success-light)", color: "var(--success)" },
    pending:    { label: "Pending", bg: "var(--warning-light)",  color: "var(--warning)"  },
    failed:     { label: "Failed",  bg: "var(--danger-light)",   color: "var(--danger)"   },
  };
  const s = map[status] ?? map.pending;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "3px 10px", borderRadius: 99,
      fontSize: 12, fontWeight: 600,
      background: s.bg, color: s.color,
    }}>
      {s.label}
    </span>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export function DailyReportsPage() {
  const { user } = useAuth();
  const isStaff = user?.role !== "investor";
  const qc = useQueryClient();
  const [triggerDate, setTriggerDate] = useState("");
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["nse-reports-week"],
    queryFn: () => nseReportsApi.list(7),
    refetchInterval: 60_000,   // refresh every minute
  });

  const trigger = useMutation({
    mutationFn: () => nseReportsApi.triggerDownload(triggerDate || undefined),
    onSuccess: (res) => {
      setTriggerMsg(res.message);
      setTimeout(() => {
        setTriggerMsg(null);
        qc.invalidateQueries({ queryKey: ["nse-reports-week"] });
      }, 3000);
    },
  });

  // ── summary stats ──────────────────────────────────────────────────────
  const records = data?.records ?? [];
  const downloaded = records.filter((r) => r.status === "downloaded").length;
  const latest = records[0];

  return (
    <div className="fade-in">
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ marginBottom: 4 }}>Daily Reports</h1>
        <p className="muted" style={{ fontSize: 14 }}>
          NSE CM-UDiFF Common Bhavcopy — auto-downloaded daily at 8:00 PM IST
        </p>
      </div>

      {/* KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 }}>
        <Card>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Files this week</p>
          <p style={{ fontSize: 26, fontWeight: 700 }}>{downloaded} / 7</p>
        </Card>
        <Card>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Last downloaded</p>
          <p style={{ fontSize: 15, fontWeight: 600 }}>
            {latest?.downloaded_at
              ? `${formatDate(latest.file_date)} · ${formatTs(latest.downloaded_at)}`
              : "—"}
          </p>
        </Card>
        <Card>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Next auto-run</p>
          <p style={{ fontSize: 15, fontWeight: 600 }}>Today · 8:00 PM IST</p>
        </Card>
      </div>

      {/* Manual trigger — staff only */}
      {isStaff && (
        <Card style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>Manual trigger</span>
            <input
              type="date"
              value={triggerDate}
              onChange={(e) => setTriggerDate(e.target.value)}
              style={{ width: 160 }}
              placeholder="Leave blank for today"
            />
            <Button
              variant="default"
              loading={trigger.isPending}
              onClick={() => trigger.mutate()}
            >
              Download now
            </Button>
            {triggerMsg && (
              <span style={{ fontSize: 13, color: "var(--success)" }}>✓ {triggerMsg}</span>
            )}
          </div>
        </Card>
      )}

      {/* Table */}
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>Last 7 days</h2>
          <span style={{
            fontSize: 12, padding: "3px 10px", borderRadius: 99,
            background: "var(--success-light)", color: "var(--success)", fontWeight: 600,
          }}>
            ● Auto-sync active
          </span>
        </div>

        {isLoading && <SkeletonTable rows={7} cols={5} />}
        {error && (
          <p style={{ color: "var(--danger)", fontSize: 14 }}>
            Failed to load reports. Please refresh.
          </p>
        )}

        {!isLoading && !error && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  {["Date", "File name", "Size", "Downloaded at", "Status", ""].map((h) => (
                    <th key={h} style={{
                      padding: "10px 14px", textAlign: "left",
                      fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
                      background: "var(--bg-secondary)",
                      borderBottom: "1px solid var(--border)",
                      whiteSpace: "nowrap",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ padding: "24px 14px", textAlign: "center", color: "var(--text-secondary)" }}>
                      No records yet — first download happens at 8:00 PM IST.
                    </td>
                  </tr>
                )}
                {records.map((r) => (
                  <tr
                    key={r.id}
                    style={{
                      background: isToday(r.file_date) ? "var(--primary-light)" : undefined,
                    }}
                  >
                    <td style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                      <strong>{formatDate(r.file_date)}</strong>
                      {isToday(r.file_date) && (
                        <span style={{
                          marginLeft: 6, fontSize: 10, padding: "2px 7px", borderRadius: 99,
                          background: "var(--primary)", color: "#fff", fontWeight: 700,
                        }}>TODAY</span>
                      )}
                    </td>
                    <td style={{
                      padding: "10px 14px", borderBottom: "1px solid var(--border)",
                      fontFamily: "monospace", fontSize: 11, color: "var(--text-secondary)",
                      maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {r.file_name}
                    </td>
                    <td style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                      {formatSize(r.file_size_bytes)}
                    </td>
                    <td style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                      {r.downloaded_at ? formatTs(r.downloaded_at) : "—"}
                    </td>
                    <td style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)" }}>
                      <StatusPill status={r.status} />
                    </td>
                    <td style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)" }}>
                      {r.status === "downloaded" && (
                        <button
                          onClick={() => nseReportsApi.download(r.file_date, r.file_name)}
                          style={{
                            display: "inline-flex", alignItems: "center", gap: 4,
                            fontSize: 12, color: "var(--primary)", fontWeight: 600,
                            padding: "4px 10px", border: "1.5px solid var(--primary)",
                            borderRadius: 8, background: "transparent", cursor: "pointer",
                          }}
                        >
                          ↓ ZIP
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-secondary)" }}>
          Showing last 7 calendar days · {data?.total ?? 0} total records in database ·{" "}
          <a href="/daily-reports/all" style={{ color: "var(--primary)" }}>View all →</a>
        </div>
      </Card>
    </div>
  );
}
