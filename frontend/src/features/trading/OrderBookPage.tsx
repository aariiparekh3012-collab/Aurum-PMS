import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tradingApi, Order } from "./api";
import { referenceApi } from "../reference/api";
import { auth } from "../../lib/auth";
import { Card, Button, StatusBadge, SkeletonTable, SkeletonKPIs, ConfirmDialog, useToast } from "../../components/ui";

const STATUS_FILTERS = ["all", "pending_approval", "approved", "rejected", "filled", "cancelled"];

const inr = (paise: number | null) =>
  paise != null
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100)
    : "—";

function NewOrderForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.securities() });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const [securityId, setSecurityId] = useState("");
  const [strategyId, setStrategyId] = useState("");
  const [side, setSide] = useState("BUY");
  const [quantity, setQuantity] = useState("");
  const [orderType, setOrderType] = useState("market");
  const [limitPrice, setLimitPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      tradingApi.createOrder({
        security_id: securityId,
        strategy_id: strategyId,
        side,
        quantity: Number(quantity),
        order_type: orderType,
        limit_price_paise: orderType === "limit" && limitPrice ? Math.round(Number(limitPrice) * 100) : undefined,
      }),
    onSuccess: () => onCreated(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = securityId && strategyId && Number(quantity) > 0;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>New Order</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>

      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Security</label>
          <select className="input" value={securityId} onChange={(e) => setSecurityId(e.target.value)}>
            <option value="">— Select —</option>
            {securities.map((s) => <option key={s.id} value={s.id}>{s.symbol} ({s.exchange})</option>)}
          </select>
        </div>
        <div>
          <label className="label">Strategy</label>
          <select className="input" value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
            <option value="">— Select —</option>
            {strategies.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
          </select>
        </div>
        <div>
          <label className="label">Side</label>
          <div className="row" style={{ gap: 8 }}>
            <button className={`btn btn--sm ${side === "BUY" ? "btn--primary" : "btn--ghost"}`} style={side === "BUY" ? { background: "var(--success)", color: "#000" } : {}} onClick={() => setSide("BUY")}>BUY</button>
            <button className={`btn btn--sm ${side === "SELL" ? "btn--primary" : "btn--ghost"}`} style={side === "SELL" ? { background: "var(--danger)", color: "#000" } : {}} onClick={() => setSide("SELL")}>SELL</button>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Quantity</label>
          <input className="input" type="number" min="1" step="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0" />
        </div>
        <div>
          <label className="label">Order Type</label>
          <select className="input" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </div>
        {orderType === "limit" && (
          <div>
            <label className="label">Limit Price (INR)</label>
            <input className="input" type="number" min="0" step="0.01" value={limitPrice} onChange={(e) => setLimitPrice(e.target.value)} placeholder="0.00" />
          </div>
        )}
      </div>

      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Place Order
      </Button>
    </Card>
  );
}

export function OrderBookPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders", filter],
    queryFn: () => tradingApi.orders(filter === "all" ? undefined : filter),
  });

  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.securities() });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.strategies() });

  const secMap = Object.fromEntries(securities.map((s) => [s.id, s.symbol]));
  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) => tradingApi.decideOrder(id, approve),
    onSuccess: (_, v) => {
      toast.success(v.approve ? "Order approved." : "Order rejected.");
      qc.invalidateQueries({ queryKey: ["orders"] });
      setRejectTarget(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const pendingCount = orders.filter((o: Order) => o.status === "pending_approval").length;
  const filledCount = orders.filter((o: Order) => o.status === "filled").length;

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Order Book</h1>
          <p className="muted">Strategy orders · compliance approval queue</p>
        </div>
        {!showForm && (
          <Button variant="primary" onClick={() => setShowForm(true)}>+ New Order</Button>
        )}
      </div>

      {showForm && (
        <NewOrderForm
          onCreated={() => {
            setShowForm(false);
            toast.success("Order placed successfully.");
            qc.invalidateQueries({ queryKey: ["orders"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {isLoading ? (
        <SkeletonKPIs count={3} />
      ) : (
        <div className="kpis" style={{ marginBottom: 20 }}>
          <div className="kpi"><span className="kpi__value">{orders.length}</span><span className="kpi__label">Total orders</span></div>
          <div className="kpi"><span className="kpi__value" style={{ color: pendingCount > 0 ? "var(--warning)" : undefined }}>{pendingCount}</span><span className="kpi__label">Pending approval</span></div>
          <div className="kpi"><span className="kpi__value">{filledCount}</span><span className="kpi__label">Filled</span></div>
        </div>
      )}

      <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((f) => (
          <button key={f} className={`btn btn--sm ${filter === f ? "btn--primary" : "btn--ghost"}`} onClick={() => setFilter(f)}>
            {f.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <Card>
        {isLoading ? (
          <SkeletonTable rows={5} cols={9} />
        ) : orders.length === 0 ? (
          <div className="empty">No orders in this view.</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Security</th><th>Strategy</th><th>Side</th><th>Qty</th><th>Type</th><th>Limit</th><th>Status</th><th>Created</th><th></th></tr>
            </thead>
            <tbody>
              {orders.map((o: Order) => (
                <tr key={o.id}>
                  <td className="mono" style={{ fontWeight: 600 }}>{secMap[o.security_id] || o.security_id.slice(0, 8)}</td>
                  <td>{stratMap[o.strategy_id] || o.strategy_id.slice(0, 8)}</td>
                  <td><span style={{ color: o.side === "BUY" ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>{o.side}</span></td>
                  <td>{o.quantity}</td>
                  <td style={{ textTransform: "capitalize" }}>{o.order_type}</td>
                  <td>{inr(o.limit_price_paise)}</td>
                  <td><StatusBadge status={o.status} /></td>
                  <td style={{ fontSize: ".78rem", color: "var(--muted)" }}>{new Date(o.created_at).toLocaleDateString("en-IN")}</td>
                  <td>
                    {o.status === "pending_approval" && isCompliance && (
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn--sm btn--primary" onClick={() => decide.mutate({ id: o.id, approve: true })}>Approve</button>
                        <button className="btn btn--sm btn--danger" onClick={() => setRejectTarget(o.id)}>Reject</button>
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
        title="Reject Order"
        message="Are you sure you want to reject this order? This action cannot be undone."
        confirmLabel="Reject"
        variant="danger"
        loading={decide.isPending}
        onConfirm={() => { if (rejectTarget) decide.mutate({ id: rejectTarget, approve: false }); }}
        onCancel={() => setRejectTarget(null)}
      />
    </div>
  );
}
