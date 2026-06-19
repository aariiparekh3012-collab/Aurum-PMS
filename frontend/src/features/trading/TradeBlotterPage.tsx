import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tradingApi, Trade } from "./api";
import { referenceApi } from "../reference/api";
import { portfolioApi, PortfolioAccount } from "../portfolio/api";
import { Card, Button, SkeletonTable, SkeletonKPIs, useToast } from "../../components/ui";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100);

function RecordTradeForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.securities() });
  const { data: brokers = [] } = useQuery({ queryKey: ["brokers"], queryFn: () => referenceApi.brokers() });
  const { data: accounts = [] } = useQuery({ queryKey: ["portfolio-accounts"], queryFn: () => portfolioApi.accounts() });

  const [securityId, setSecurityId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [brokerId, setBrokerId] = useState("");
  const [side, setSide] = useState("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [contractNote, setContractNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const record = useMutation({
    mutationFn: () =>
      tradingApi.recordTrade({
        security_id: securityId,
        portfolio_account_id: accountId,
        broker_id: brokerId,
        side,
        quantity: Number(quantity),
        price_paise: Math.round(Number(price) * 100),
        contract_note: contractNote || undefined,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = securityId && accountId && brokerId && Number(quantity) > 0 && Number(price) > 0;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>Record Trade</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>

      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Security</label>
          <select className="input" value={securityId} onChange={(e) => setSecurityId(e.target.value)}>
            <option value="">— Select —</option>
            {securities.map((s) => <option key={s.id} value={s.id}>{s.symbol}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Portfolio Account</label>
          <select className="input" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">— Select —</option>
            {accounts.map((a: PortfolioAccount) => <option key={a.id} value={a.id}>{a.account_code}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Broker</label>
          <select className="input" value={brokerId} onChange={(e) => setBrokerId(e.target.value)}>
            <option value="">— Select —</option>
            {brokers.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Side</label>
          <div className="row" style={{ gap: 8 }}>
            <button className={`btn btn--sm ${side === "BUY" ? "btn--primary" : "btn--ghost"}`} style={side === "BUY" ? { background: "var(--success)", color: "#000" } : {}} onClick={() => setSide("BUY")}>BUY</button>
            <button className={`btn btn--sm ${side === "SELL" ? "btn--primary" : "btn--ghost"}`} style={side === "SELL" ? { background: "var(--danger)", color: "#000" } : {}} onClick={() => setSide("SELL")}>SELL</button>
          </div>
        </div>
        <div>
          <label className="label">Quantity</label>
          <input className="input" type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0" />
        </div>
        <div>
          <label className="label">Price (INR)</label>
          <input className="input" type="number" min="0" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="0.00" />
        </div>
        <div>
          <label className="label">Contract Note</label>
          <input className="input" value={contractNote} onChange={(e) => setContractNote(e.target.value)} placeholder="Optional" />
        </div>
      </div>

      <Button variant="primary" disabled={!valid} loading={record.isPending} onClick={() => record.mutate()}>
        Record Trade
      </Button>
    </Card>
  );
}

export function TradeBlotterPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const { data: trades = [], isLoading } = useQuery({ queryKey: ["trades"], queryFn: () => tradingApi.trades() });
  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.securities() });
  const { data: brokers = [] } = useQuery({ queryKey: ["brokers"], queryFn: () => referenceApi.brokers() });

  const secMap = Object.fromEntries(securities.map((s) => [s.id, s.symbol]));
  const brokerMap = Object.fromEntries(brokers.map((b) => [b.id, b.name]));

  const filtered = trades.filter((t: Trade) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (secMap[t.security_id] || "").toLowerCase().includes(q) || t.side.toLowerCase().includes(q);
  });

  const buyCount = trades.filter((t: Trade) => t.side === "BUY" || t.side === "buy").length;
  const sellCount = trades.filter((t: Trade) => t.side === "SELL" || t.side === "sell").length;

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Trade Blotter</h1>
          <p className="muted">Executed trades across all portfolios</p>
        </div>
        {!showForm && <Button variant="primary" onClick={() => setShowForm(true)}>+ Record Trade</Button>}
      </div>

      {showForm && (
        <RecordTradeForm
          onDone={() => {
            setShowForm(false);
            toast.success("Trade recorded successfully.");
            qc.invalidateQueries({ queryKey: ["trades"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {isLoading ? (
        <SkeletonKPIs count={3} />
      ) : (
        <div className="kpis" style={{ marginBottom: 24 }}>
          <div className="kpi"><span className="kpi__value">{trades.length}</span><span className="kpi__label">Total trades</span></div>
          <div className="kpi"><span className="kpi__value" style={{ color: "var(--success)" }}>{buyCount}</span><span className="kpi__label">Buys</span></div>
          <div className="kpi"><span className="kpi__value" style={{ color: "var(--danger)" }}>{sellCount}</span><span className="kpi__label">Sells</span></div>
        </div>
      )}

      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Blotter</h2>
          <input className="input" style={{ maxWidth: 260 }} placeholder="Filter by symbol..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>

        {isLoading ? (
          <SkeletonTable rows={5} cols={8} />
        ) : filtered.length === 0 ? (
          <div className="empty">No trades recorded yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Security</th><th>Side</th><th>Qty</th><th>Price</th><th>Value</th><th>Broker</th><th>Traded</th><th>Contract</th></tr>
            </thead>
            <tbody>
              {filtered.map((t: Trade) => (
                <tr key={t.id}>
                  <td className="mono" style={{ fontWeight: 600 }}>{secMap[t.security_id] || t.security_id.slice(0, 8)}</td>
                  <td><span style={{ color: t.side === "BUY" || t.side === "buy" ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>{t.side.toUpperCase()}</span></td>
                  <td>{t.quantity}</td>
                  <td>{inr(t.price_paise)}</td>
                  <td>{inr(t.price_paise * t.quantity)}</td>
                  <td>{brokerMap[t.broker_id] || "—"}</td>
                  <td style={{ fontSize: ".78rem" }}>{new Date(t.traded_at).toLocaleDateString("en-IN")}</td>
                  <td className="mono" style={{ fontSize: ".78rem" }}>{t.contract_note || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
