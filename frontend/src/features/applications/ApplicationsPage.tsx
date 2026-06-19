import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "./api";
import { clientsApi } from "../clients/api";
import { auth } from "../../lib/auth";
import { Button, Card, StatusBadge, ConfirmDialog, SkeletonTable, useToast } from "../../components/ui";

const FILTERS = ["all", "under_review", "active", "kyc_rejected", "rejected"];

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export function ApplicationsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState("all");
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications", filter],
    queryFn: () => applicationsApi.list(filter === "all" ? undefined : filter),
  });

  const decide = useMutation({
    mutationFn: ({ id, approve, reason }: { id: string; approve: boolean; reason?: string }) =>
      applicationsApi.decide(id, approve, reason),
    onSuccess: (_, v) => {
      toast.success(v.approve ? "Application approved." : "Application rejected.");
      qc.invalidateQueries({ queryKey: ["applications"] });
      setRejectTarget(null);
      setRejectReason("");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const provision = useMutation({
    mutationFn: clientsApi.processOutbox,
    onSuccess: (r) => {
      toast.success(`Provisioned ${r.processed} client(s).`);
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Applications</h1>
          <p className="muted">Compliance review queue · maker-checker</p>
        </div>
        {isCompliance && (
          <Button variant="primary" loading={provision.isPending} onClick={() => provision.mutate()}>
            Provision approved &rarr; clients
          </Button>
        )}
      </div>

      <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`btn btn--sm ${filter === f ? "btn--primary" : "btn--ghost"}`}
            onClick={() => setFilter(f)}
          >
            {f.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <Card>
        {isLoading ? (
          <SkeletonTable rows={5} cols={6} />
        ) : apps.length === 0 ? (
          <div className="empty">No applications in this view.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Applicant</th><th>PAN</th><th>Investment</th>
                <th>Risk</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id} style={{ cursor: "default" }}>
                  <td>
                    {a.full_name}
                    <div className="faint" style={{ fontSize: ".78rem" }}>{a.email}</div>
                  </td>
                  <td className="mono">{a.pan}</td>
                  <td>{inr(a.proposed_investment_inr)}</td>
                  <td style={{ textTransform: "capitalize" }}>{a.risk_category ?? "—"}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td>
                    {a.status === "under_review" && isCompliance && (
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn--sm btn--primary"
                          onClick={() => decide.mutate({ id: a.id, approve: true })}>
                          Approve
                        </button>
                        <button className="btn btn--sm btn--danger" onClick={() => setRejectTarget(a.id)}>
                          Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <ConfirmDialog
        open={!!rejectTarget}
        title="Reject Application"
        message="This action cannot be undone. Provide a reason for rejection."
        confirmLabel="Reject"
        variant="danger"
        loading={decide.isPending}
        onConfirm={() => {
          if (!rejectReason.trim()) {
            toast.error("A rejection reason is required.");
            return;
          }
          if (rejectTarget) {
            decide.mutate({ id: rejectTarget, approve: false, reason: rejectReason });
          }
        }}
        onCancel={() => { setRejectTarget(null); setRejectReason(""); }}
      >
        <div className="field">
          <label className="label">Reason</label>
          <textarea
            className="input"
            rows={3}
            placeholder="e.g. KYC documents incomplete..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
        </div>
      </ConfirmDialog>
    </div>
  );
}
