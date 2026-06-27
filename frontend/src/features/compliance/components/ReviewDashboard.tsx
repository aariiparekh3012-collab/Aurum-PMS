import { useState, useEffect } from "react";
import { apiClient } from "@/lib/apiClient";
import type { ApplicationResponse } from "@/features/onboarding/types";

const STATUS_TABS = [
  { key: "under_review", label: "Under Review" },
  { key: "active", label: "Active" },
  { key: "rejected", label: "Rejected" },
  { key: "kyc_pending", label: "KYC Pending" },
  { key: "draft", label: "Drafts" },
];

export default function ReviewDashboard() {
  const [tab, setTab] = useState("under_review");
  const [apps, setApps] = useState<ApplicationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ApplicationResponse | null>(null);
  const [reason, setReason] = useState("");
  const [acting, setActing] = useState(false);

  const fetchApps = async (status: string) => {
    setLoading(true);
    try {
      const { data } = await apiClient.get<any>("/onboarding/applications", {
        params: { status },
      });
      setApps(Array.isArray(data) ? data : data.applications ?? []);
    } catch { setApps([]); }
    setLoading(false);
  };

  useEffect(() => { fetchApps(tab); }, [tab]);

  const handleDecision = async (approve: boolean) => {
    if (!selected) return;
    if (!approve && !reason.trim()) { alert("Rejection reason is required"); return; }
    setActing(true);
    try {
      await apiClient.post(`/onboarding/applications/${selected.id}/decision`, {
        approve, reason: approve ? null : reason,
      });
      setSelected(null);
      setReason("");
      fetchApps(tab);
    } catch (err: any) {
      alert(err.message);
    }
    setActing(false);
  };

  const statusBadge = (s: string) => {
    const map: Record<string, string> = {
      draft: "badge-draft", kyc_pending: "badge-pending", kyc_verified: "badge-verified",
      kyc_rejected: "badge-rejected", risk_profiled: "badge-verified",
      agreement_pending: "badge-pending", agreement_signed: "badge-verified",
      under_review: "badge-pending", active: "badge-active", rejected: "badge-rejected",
    };
    return <span className={`badge ${map[s] || "badge-draft"}`}>{s.replace(/_/g, " ")}</span>;
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Compliance Review</h1>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
        Maker-checker review queue for onboarding applications
      </p>

      <div style={{ display: "flex", gap: 4, marginBottom: 20 }}>
        {STATUS_TABS.map((t) => (
          <button key={t.key} className={`btn ${tab === t.key ? "btn-primary" : "btn-outline"}`}
            style={{ padding: "6px 14px", fontSize: 13 }} onClick={() => { setTab(t.key); setSelected(null); }}>
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: 16 }}>
        <div>
          {loading ? (
            <p style={{ color: "var(--text-secondary)", padding: 20 }}>Loading...</p>
          ) : apps.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", padding: 20 }}>No applications in this status.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {apps.map((app) => (
                <div key={app.id} className="card" onClick={() => setSelected(app)}
                  style={{
                    cursor: "pointer", padding: 16,
                    borderColor: selected?.id === app.id ? "var(--primary)" : undefined,
                  }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{app.full_name}</span>
                    {statusBadge(app.status)}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {app.email} · {app.investor_type} · ₹{(app.proposed_investment_inr / 100000).toFixed(1)}L
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Application Details</h3>
            <div style={{ fontSize: 14, lineHeight: 2 }}>
              <div><strong>ID:</strong> <code style={{ fontSize: 12 }}>{selected.id}</code></div>
              <div><strong>Name:</strong> {selected.full_name}</div>
              <div><strong>Email:</strong> {selected.email}</div>
              <div><strong>Type:</strong> {selected.investor_type}</div>
              <div><strong>PAN:</strong> {selected.pan}</div>
              <div><strong>Investment:</strong> ₹{selected.proposed_investment_inr.toLocaleString("en-IN")}</div>
              <div><strong>Status:</strong> {statusBadge(selected.status)}</div>
              {selected.risk_category && <div><strong>Risk:</strong> {selected.risk_category}</div>}
              {selected.kyc_source && <div><strong>KYC Source:</strong> {selected.kyc_source}</div>}
            </div>

            {selected.status === "under_review" && (
              <div style={{ marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
                <label>Rejection reason (required if rejecting)</label>
                <textarea value={reason} onChange={(e) => setReason(e.target.value)}
                  rows={3} placeholder="Reason for rejection..." style={{ marginBottom: 12 }} />
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-success" onClick={() => handleDecision(true)} disabled={acting}>
                    {acting ? "..." : "Approve"}
                  </button>
                  <button className="btn btn-danger" onClick={() => handleDecision(false)} disabled={acting}>
                    {acting ? "..." : "Reject"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
