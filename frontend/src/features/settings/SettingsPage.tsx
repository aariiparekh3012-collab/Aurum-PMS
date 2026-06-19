import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { auth } from "../../lib/auth";
import { authApi } from "../auth/api";
import { Card, Button, ConfirmDialog, SkeletonTable, useToast } from "../../components/ui";

interface Prefs {
  email_enabled: boolean;
  order_alerts: boolean;
  trade_alerts: boolean;
  application_alerts: boolean;
}

export function SettingsPage() {
  const user = auth.getUser();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState<"profile" | "notifications" | "sessions" | "appearance">("profile");
  const [logoutConfirm, setLogoutConfirm] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null);

  const [localPrefs, setLocalPrefs] = useState<Prefs>({
    email_enabled: true,
    order_alerts: true,
    trade_alerts: true,
    application_alerts: true,
  });

  const togglePref = (key: keyof Prefs) =>
    setLocalPrefs((p) => ({ ...p, [key]: !p[key] }));

  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ["auth-sessions"],
    queryFn: authApi.sessions,
    enabled: tab === "sessions",
  });

  const revokeSession = useMutation({
    mutationFn: (id: string) => authApi.revokeSession(id),
    onSuccess: () => {
      toast.success("Session revoked.");
      setRevokeTarget(null);
      qc.invalidateQueries({ queryKey: ["auth-sessions"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Best effort
    }
    auth.clear();
    navigate("/login");
  };

  return (
    <div className="fade-in">
      <div className="row row--between" style={{ marginBottom: 24 }}>
        <div>
          <h1>Settings</h1>
          <p className="muted">Manage your profile, notifications, and sessions</p>
        </div>
        <Button variant="danger" onClick={() => setLogoutConfirm(true)}>Sign out</Button>
      </div>

      <div className="row" style={{ gap: 8, marginBottom: 24 }}>
        {(["profile", "notifications", "sessions", "appearance"] as const).map((t) => (
          <button
            key={t}
            className={`btn btn--sm ${tab === t ? "btn--primary" : "btn--ghost"}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <Card>
            <h2 style={{ marginBottom: 20 }}>User Profile</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
              <div
                className="avatar"
                style={{
                  width: 64, height: 64, fontSize: "1.6rem",
                  background: "linear-gradient(135deg, var(--gold), var(--gold-2))",
                  color: "#1a1305",
                }}
              >
                {(user?.full_name ?? user?.subject ?? "U")[0].toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
                  {user?.full_name ?? user?.subject ?? "Guest"}
                </div>
                <div className="muted" style={{ textTransform: "capitalize" }}>{user?.role ?? "unknown"}</div>
              </div>
            </div>
            <div style={{ display: "grid", gap: 12 }}>
              {[
                { label: "Email", value: user?.email ?? user?.subject ?? "—" },
                { label: "Role", value: user?.role ?? "—" },
                {
                  label: "Email verified",
                  value: user?.email_verified
                    ? <span className="badge badge--success">Verified</span>
                    : <span className="badge badge--warning">Pending</span>,
                },
              ].map(({ label, value }) => (
                <div key={label} className="row row--between" style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                  <span className="muted" style={{ fontSize: ".85rem" }}>{label}</span>
                  <span style={{ textTransform: label === "Role" ? "capitalize" : "none" }}>{value}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h2 style={{ marginBottom: 20 }}>Role Permissions</h2>
            <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
              Access levels are determined by your assigned role.
            </p>
            <div style={{ display: "grid", gap: 8 }}>
              {(user?.role === "compliance"
                ? [
                    "View all clients & applications",
                    "Approve / reject applications",
                    "Provision clients from approved apps",
                    "Manage securities, strategies, brokers",
                    "View & generate reports",
                    "Access compliance review queue",
                    "Manage fee schedules",
                  ]
                : user?.role === "rm"
                ? [
                    "View all clients & applications",
                    "Submit new onboarding applications",
                    "Create orders and record trades",
                    "Manage portfolio accounts",
                    "View & generate reports",
                  ]
                : [
                    "View own portfolio holdings",
                    "View own cash ledger",
                    "Track onboarding status",
                    "View reports & activity feed",
                  ]
              ).map((p) => (
                <div key={p} className="row" style={{ gap: 8, fontSize: ".88rem" }}>
                  <span style={{ color: "var(--success)" }}>✓</span> {p}
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {tab === "notifications" && (
        <Card style={{ maxWidth: 600 }}>
          <h2 style={{ marginBottom: 20 }}>Notification Preferences</h2>
          <div style={{ display: "grid", gap: 0 }}>
            {([
              { key: "email_enabled" as const, label: "Email notifications", desc: "Receive email alerts for important events" },
              { key: "order_alerts" as const, label: "Order alerts", desc: "New orders, approvals, and rejections" },
              { key: "trade_alerts" as const, label: "Trade alerts", desc: "Trade executions and confirmations" },
              { key: "application_alerts" as const, label: "Application alerts", desc: "Onboarding status changes" },
            ]).map(({ key, label, desc }) => (
              <div
                key={key}
                className="row row--between"
                style={{ padding: "16px 0", borderBottom: "1px solid var(--line)", cursor: "pointer" }}
                onClick={() => togglePref(key)}
              >
                <div>
                  <div style={{ fontWeight: 500, marginBottom: 2 }}>{label}</div>
                  <div className="muted" style={{ fontSize: ".82rem" }}>{desc}</div>
                </div>
                <div className={`toggle ${localPrefs[key] ? "toggle--on" : ""}`} />
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20 }}>
            <Button variant="primary" onClick={() => toast.success("Preferences saved.")}>
              Save Preferences
            </Button>
          </div>
        </Card>
      )}

      {tab === "sessions" && (
        <Card style={{ maxWidth: 700 }}>
          <h2 style={{ marginBottom: 20 }}>Active Sessions</h2>
          <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
            Devices and browsers where you are currently signed in.
          </p>
          {sessionsLoading ? (
            <SkeletonTable rows={3} cols={4} />
          ) : sessions.length === 0 ? (
            <div className="empty">No active sessions found. You may be using a dev token.</div>
          ) : (
            <div style={{ display: "grid", gap: 0 }}>
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="row row--between"
                  style={{ padding: "14px 0", borderBottom: "1px solid var(--line)" }}
                >
                  <div>
                    <div style={{ fontSize: ".9rem", fontWeight: 500 }}>
                      {s.device_info ? s.device_info.slice(0, 60) : "Unknown device"}
                    </div>
                    <div className="muted" style={{ fontSize: ".78rem", marginTop: 2 }}>
                      IP: {s.ip_address ?? "—"} · Started: {new Date(s.created_at).toLocaleDateString("en-IN")}
                    </div>
                  </div>
                  <Button variant="ghost" onClick={() => setRevokeTarget(s.id)}>
                    Revoke
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "appearance" && (
        <Card style={{ maxWidth: 600 }}>
          <h2 style={{ marginBottom: 20 }}>Appearance</h2>
          <div style={{ display: "grid", gap: 16 }}>
            {[
              { label: "Theme", desc: "Dark mode with gold accents", value: <span className="badge badge--gold">Premium Dark</span> },
              { label: "Currency display", desc: "Format for monetary values", value: <span className="mono">INR</span> },
              { label: "Date format", desc: "How dates are displayed", value: <span className="mono">DD/MM/YYYY</span> },
              { label: "Timezone", desc: "Market hours reference", value: <span>IST (UTC+5:30)</span> },
            ].map(({ label, desc, value }) => (
              <div key={label} className="row row--between" style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{label}</div>
                  <div className="muted" style={{ fontSize: ".82rem" }}>{desc}</div>
                </div>
                {value}
              </div>
            ))}
          </div>
        </Card>
      )}

      <ConfirmDialog
        open={logoutConfirm}
        title="Sign Out"
        message="You will be signed out of this session. You can sign back in anytime."
        confirmLabel="Sign Out"
        variant="danger"
        onConfirm={handleLogout}
        onCancel={() => setLogoutConfirm(false)}
      />

      <ConfirmDialog
        open={!!revokeTarget}
        title="Revoke Session"
        message="This will sign out the device associated with this session."
        confirmLabel="Revoke"
        variant="danger"
        loading={revokeSession.isPending}
        onConfirm={() => { if (revokeTarget) revokeSession.mutate(revokeTarget); }}
        onCancel={() => setRevokeTarget(null)}
      />
    </div>
  );
}
