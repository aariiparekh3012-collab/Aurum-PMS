import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Button } from "../../components/ui";
import { complianceApi } from "./api";

interface ReviewApplication {
  id: string;
  full_name: string;
  email: string;
  mobile: string;
  investor_type: string;
  proposed_investment_inr: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export function ComplianceReviewPage() {
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);

  const { data: reviewData, isLoading } = useQuery({
    queryKey: ["compliance", "review", offset],
    queryFn: () => complianceApi.listForReview(limit, offset),
  });

  const applications = (reviewData as any)?.applications || [];
  const total = (reviewData as any)?.total || 0;

  const handleRowClick = (appId: string) => {
    setSelectedId(appId);
    navigate("/compliance/review/" + appId);
  };

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);

  const formatDate = (isoString: string) => new Date(isoString).toLocaleDateString("en-IN");

  if (isLoading) {
    return <div className="empty"><span className="spinner" /> Loading applications...</div>;
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>Compliance Review Queue</h1>
        <p className="muted">Applications pending maker-checker approval</p>
      </div>

      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <div>
            <strong>{total}</strong> <span className="muted">applications awaiting review</span>
          </div>
        </div>

        {applications.length === 0 ? (
          <div className="empty"><p>No applications pending review.</p></div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Contact</th>
                <th>Type</th>
                <th>Investment</th>
                <th>Submitted</th>
                <th style={{ textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app: ReviewApplication) => (
                <tr key={app.id} style={{ cursor: "pointer", backgroundColor: selectedId === app.id ? "var(--bg-secondary)" : "" }}>
                  <td style={{ fontWeight: 500 }}>{app.full_name}</td>
                  <td>
                    <div style={{ fontSize: "0.9rem" }}>{app.email}</div>
                    <div className="muted" style={{ fontSize: "0.85rem" }}>{app.mobile}</div>
                  </td>
                  <td style={{ textTransform: "capitalize", fontSize: "0.9rem" }}>
                    {app.investor_type.replace(/_/g, " ")}
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 500 }}>{formatCurrency(app.proposed_investment_inr)}</td>
                  <td style={{ fontSize: "0.9rem" }}>{formatDate(app.created_at)}</td>
                  <td style={{ textAlign: "center" }}>
                    <Button variant="primary" className="btn--sm" onClick={() => handleRowClick(app.id)}>
                      Review
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {total > limit && (
          <div className="row row--between" style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
            <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
              &larr; Previous
            </Button>
            <span className="muted">Page {Math.floor(offset / limit) + 1} of {Math.ceil(total / limit)}</span>
            <Button variant="ghost" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
              Next &rarr;
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
