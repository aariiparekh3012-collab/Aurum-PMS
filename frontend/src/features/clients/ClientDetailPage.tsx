import type React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { clientsApi } from "./api";
import { portfolioApi } from "../portfolio/api";
import { Card, StatusBadge, Button } from "../../components/ui";


function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="row row--between" style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
      <span className="muted" style={{ fontSize: ".85rem" }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function AccountHoldingCount({ accountId }: { accountId: string }) {
  const { data: holdings = [] } = useQuery({
    queryKey: ["holdings", accountId],
    queryFn: () => portfolioApi.holdings(accountId),
  });
  return <span className="muted">{holdings.length} securities</span>;
}

export function ClientDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const { data: c, isLoading, error } = useQuery({
    queryKey: ["client", id],
    queryFn: () => clientsApi.get(id),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["portfolio-accounts", id],
    queryFn: () => portfolioApi.accounts(id),
    enabled: !!id,
  });

  if (isLoading) return <div className="empty"><span className="spinner" /> Loading…</div>;
  if (error || !c) return <div className="empty">Client not found.</div>;

  return (
    <div className="fade-in" style={{ maxWidth: 860 }}>
      <Link to="/clients" className="muted" style={{ fontSize: ".85rem" }}>← Back to clients</Link>

      <div className="row row--between" style={{ margin: "12px 0 24px" }}>
        <div className="row">
          <div className="avatar" style={{ width: 52, height: 52, fontSize: "1.3rem" }}>
            {c.full_name[0]}
          </div>
          <div>
            <h1 style={{ marginBottom: 2 }}>{c.full_name}</h1>
            <span className="mono">{c.client_code}</span>
          </div>
        </div>
        <StatusBadge status={c.status} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Card>
          <h2 className="card__title">Profile</h2>
          <Row label="PAN" value={<span className="mono">{c.pan}</span>} />
          <Row label="Investor type" value={<span style={{ textTransform: "capitalize" }}>{c.investor_type}</span>} />
          <Row label="Email" value={c.email} />
          <Row label="Mobile" value={c.mobile} />
          <Row label="Risk profile" value={
            c.risk_category
              ? <span className="badge badge--gold" style={{ textTransform: "capitalize" }}>{c.risk_category}</span>
              : "—"
          } />
        </Card>

        <Card>
          <h2 className="card__title">Bank &amp; Demat</h2>
          {c.bank_accounts.length === 0 ? <p className="faint">No bank accounts.</p> :
            c.bank_accounts.map((b, i) => (
              <Row key={i} label={`${b.ifsc}${b.is_primary ? " · primary" : ""}`}
                value={<span className="mono">{b.masked_account}</span>} />
            ))}
          {c.demat_bo_ids.map((d, i) => (
            <Row key={`d${i}`} label="Demat BO ID" value={<span className="mono">{d}</span>} />
          ))}
        </Card>

        {accounts.length > 0 && (
          <Card style={{ gridColumn: "1 / -1" }}>
            <div className="row row--between" style={{ marginBottom: 12 }}>
              <h2 className="card__title" style={{ marginBottom: 0 }}>Portfolio Accounts</h2>
              <Button variant="ghost" onClick={() => navigate("/holdings")}>View all holdings</Button>
            </div>
            <table className="table">
              <thead>
                <tr><th>Account</th><th>Status</th><th>Inception</th><th>Holdings</th><th></th></tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id}>
                    <td><span className="mono" style={{ fontWeight: 600 }}>{a.account_code}</span></td>
                    <td><StatusBadge status={a.status} /></td>
                    <td className="muted">{a.inception_date}</td>
                    <td><AccountHoldingCount accountId={a.id} /></td>
                    <td>
                      <Button variant="ghost" onClick={() => navigate("/performance")}>
                        Performance →
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        <Card style={{ gridColumn: "1 / -1" }}>
          <h2 className="card__title">Nominees</h2>
          {c.nominees.length === 0 ? (
            <p className="faint">No nominees on record yet.</p>
          ) : (
            <table className="table">
              <thead><tr><th>Rank</th><th>Name</th><th>Relationship</th><th>Share %</th></tr></thead>
              <tbody>
                {c.nominees.map((n, i) => (
                  <tr key={i} style={{ cursor: "default" }}>
                    <td>{n.rank}</td><td>{n.name}</td>
                    <td>{n.relationship ?? "—"}</td><td>{n.share_percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
