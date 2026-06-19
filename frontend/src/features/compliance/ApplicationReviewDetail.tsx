import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, Button, StatusBadge } from "../../components/ui";
import { complianceApi, ReviewApplication } from "./api";

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export function ApplicationReviewDetail() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();
  const [decision, setDecision] = useState<"approve" | "reject" | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: detail, isLoading } = useQuery<ReviewApplication>({
    queryKey: ["application", applicationId],
    queryFn: () => complianceApi.getApplicationDetail(applicationId!),
    enabled: !!applicationId,
  });

  const approveMutation = useMutation({
    mutationFn: () => complianceApi.approveApplication(applicationId!),
    onSuccess: () => navigate("/compliance/review"),
    onError: (err: any) => setError((err as Error).message || "Failed to approve application"),
  });

  const rejectMutation = useMutation({
    mutationFn: () => complianceApi.rejectApplication(applicationId!, rejectionReason),
    onSuccess: () => navigate("/compliance/review"),
    onError: (err: any) => setError((err as Error).message || "Failed to reject application"),
  });

  const handleSubmit = () => {
    setError(null);
    if (decision === "approve") approveMutation.mutate();
    else if (decision === "reject") {
      if (!rejectionReason.trim()) { setError("Rejection reason is required"); return; }
      rejectMutation.mutate();
    }
  };

  if (isLoading) return <div className="empty"><span className="spinner" /> Loading application...</div>;
  if (!detail) return <div className="empty">Application not found.</div>;

  const isProcessing = approveMutation.isPending || rejectMutation.isPending;

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <Button variant="ghost" onClick={() => navigate("/compliance/review")}>&larr; Back to queue</Button>
        <h1 style={{ marginTop: 16 }}>Review Application</h1>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "2fr 1fr", gap: 24 }}>
        <Card>
          <div style={{ marginBottom: 24 }}>
            <div className="row" style={{ gap: 12, marginBottom: 8 }}>
              <h2>{detail.full_name}</h2>
              <StatusBadge status={detail.status} />
            </div>
            <p className="muted">{detail.email} · {detail.mobile}</p>
          </div>

          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24, paddingBottom: 24, borderBottom: "1px solid var(--border)" }}>
            <div>
              <div className="muted" style={{ fontSize: ".85rem", marginBottom: 4 }}>Investor Type</div>
              <div style={{ fontWeight: 500, textTransform: "capitalize" }}>{(detail.investor_type || "").replace(/_/g, " ")}</div>
            </div>
            <div>
              <div className="muted" style={{ fontSize: ".85rem", marginBottom: 4 }}>Proposed Investment</div>
              <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>{inr(detail.proposed_investment_inr || 0)}</div>
            </div>
            <div>
              <div className="muted" style={{ fontSize: ".85rem", marginBottom: 4 }}>Risk Category</div>
              <div style={{ textTransform: "capitalize" }}>{detail.risk_category || "Not yet profiled"}</div>
            </div>
            <div>
              <div className="muted" style={{ fontSize: ".85rem", marginBottom: 4 }}>PAN</div>
              <div className="mono">{detail.pan || "N/A"}</div>
            </div>
          </div>
        </Card>

        <Card style={{ height: "fit-content", position: "sticky", top: 20 }}>
          <h3 style={{ marginBottom: 20 }}>Compliance Decision</h3>

          {error && (
            <div style={{ padding: 12, backgroundColor: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, fontSize: ".9rem", color: "var(--danger)" }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", marginBottom: 8, cursor: "pointer" }}>
              <input type="radio" name="decision" value="approve" checked={decision === "approve"}
                onChange={() => { setDecision("approve"); setError(null); }} disabled={isProcessing} />
              <span style={{ marginLeft: 8 }}>Approve Application</span>
            </label>
            <label style={{ display: "block", marginBottom: 12, cursor: "pointer" }}>
              <input type="radio" name="decision" value="reject" checked={decision === "reject"}
                onChange={() => { setDecision("reject"); setError(null); }} disabled={isProcessing} />
              <span style={{ marginLeft: 8 }}>Reject Application</span>
            </label>
          </div>

          {decision === "reject" && (
            <div style={{ marginBottom: 20 }}>
              <label className="label">Rejection Reason <span style={{ color: "var(--danger)" }}>*</span></label>
              <textarea
                className="input"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Explain why..."
                disabled={isProcessing}
                style={{ minHeight: 100, resize: "vertical" }}
              />
            </div>
          )}

          <div className="row" style={{ gap: 8 }}>
            <Button variant="primary" disabled={decision === null || isProcessing} onClick={handleSubmit} loading={isProcessing}>
              {decision === "approve" ? "Approve" : decision === "reject" ? "Reject" : "Decide"}
            </Button>
            <Button variant="ghost" disabled={isProcessing} onClick={() => navigate("/compliance/review")}>Cancel</Button>
          </div>

          <div className="muted" style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)", fontSize: ".82rem" }}>
            All decisions are logged and audited per SEBI PMS Regulations.
          </div>
        </Card>
      </div>
    </div>
  );
}
