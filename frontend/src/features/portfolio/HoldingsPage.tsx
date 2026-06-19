import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { portfolioApi, PortfolioAccount, Holding } from "./api";
import { referenceApi } from "../reference/api";
import { clientsApi } from "../clients/api";
import { Card, Button, Toast } from "../../components/ui";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100);

function NewAccountForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const { data: clients = [] } = useQuery({ queryKey: ["clients"], queryFn: clientsApi.list });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const [clientId, setClientId] = useState("");
  const [strategyId, setStrategyId] = useState("");
  const [accountCode, setAccountCode] = useState("");
  const [inceptionDate, setInceptionDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      portfolioApi.createAccount({
        client_id: clientId,
        strategy_id: strategyId,
        account_code: accountCode,
        inception_date: inceptionDate,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = clientId && strategyId && accountCode.trim() && inceptionDate;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>New Portfolio Account</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>

      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Client</label>
          <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">— Select client —</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.full_name} ({c.client_code})</option>)}
          </select>
        </div>
        <div>
          <label className="label">Strategy</label>
          <select className="input" value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
            <option value="">— Select strategy —</option>
            {strategies.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Account Code</label>
          <input className="input" value={accountCode} onChange={(e) => setAccountCode(e.target.value.toUpperCase())} placeholder="e.g. PMS-001-LCV" />
        </div>
        <div>
          <label className="label">Inception Date</label>
          <input className="input" type="date" value={inceptionDate} onChange={(e) => setInceptionDate(e.target.value)} />
        </div>
      </div>

      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Create Account
      </Button>
    </Card>
  );
}

export function HoldingsPage() {
  const qc = useQueryClient();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);

  const { data: accounts = [], isLoading: loadingAccounts } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.accounts(),
  });

  const { data: holdings = [], isLoading: loadingHoldings } = useQuery({
    queryKey: ["holdings", selectedAccount],
    queryFn: () => (selectedAccount ? portfolioApi.holdings(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.securities() });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const secMap = Object.fromEntries(securities.map((s) => [s.id, s]));
  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const totalCost = holdings.reduce((sum: number, h: Holding) => sum + h.avg_cost_paise * h.quantity, 0);

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Portfolio Holdings</h1>
          <p className="muted">View holdings by portfolio account</p>
        </div>
        {!showForm && <Button variant="primary" onClick={() => setShowForm(true)}>+ New Account</Button>}
      </div>

      {showForm && (
        <NewAccountForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Portfolio account created.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["portfolio-accounts"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi"><span className="kpi__value">{accounts.length}</span><span className="kpi__label">Portfolio accounts</span></div>
        <div className="kpi"><span className="kpi__value">{holdings.length}</span><span className="kpi__label">Positions</span></div>
        {totalCost > 0 && <div className="kpi"><span className="kpi__value">{inr(totalCost)}</span><span className="kpi__label">Total cost</span></div>}
      </div>

      <Card>
        <h2 style={{ marginBottom: 16 }}>Accounts</h2>
        {loadingAccounts ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : accounts.length === 0 ? (
          <div className="empty">No portfolio accounts yet. Create one after onboarding a client.</div>
        ) : (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
            {accounts.map((a: PortfolioAccount) => (
              <button key={a.id} className={`btn ${selectedAccount === a.id ? "btn--primary" : "btn--ghost"}`} onClick={() => setSelectedAccount(a.id)}>
                {a.account_code}
                <span className="faint" style={{ marginLeft: 6, fontSize: ".8rem" }}>{stratMap[a.strategy_id] || ""}</span>
              </button>
            ))}
          </div>
        )}
      </Card>

      {selectedAccount && (
        <Card style={{ marginTop: 20 }}>
          <h2 style={{ marginBottom: 16 }}>
            Holdings — {accounts.find((a: PortfolioAccount) => a.id === selectedAccount)?.account_code}
          </h2>
          {loadingHoldings ? (
            <div className="empty"><span className="spinner" /> Loading...</div>
          ) : holdings.length === 0 ? (
            <div className="empty">No holdings in this account.</div>
          ) : (
            <table className="table">
              <thead><tr><th>Security</th><th>ISIN</th><th>Sector</th><th>Qty</th><th>Avg Cost</th><th>Cost Value</th></tr></thead>
              <tbody>
                {holdings.map((h: Holding) => {
                  const sec = secMap[h.security_id];
                  return (
                    <tr key={h.id}>
                      <td className="mono" style={{ fontWeight: 600 }}>{sec?.symbol || h.security_id.slice(0, 8)}</td>
                      <td className="mono">{sec?.isin || "—"}</td>
                      <td>{sec?.sector || "—"}</td>
                      <td>{h.quantity}</td>
                      <td>{inr(h.avg_cost_paise)}</td>
                      <td>{inr(h.avg_cost_paise * h.quantity)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      )}
      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </div>
  );
}
