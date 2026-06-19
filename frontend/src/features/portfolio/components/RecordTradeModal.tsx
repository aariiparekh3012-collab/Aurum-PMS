import { useState } from "react";
import { useRecordTrade, useSecurities } from "../hooks/usePortfolio";
import type { Security } from "../types";

interface Props {
  accountId: string;
  onClose: () => void;
}

export default function RecordTradeModal({ accountId, onClose }: Props) {
  const { data: securities = [] } = useSecurities();
  const trade = useRecordTrade(accountId);

  const [securityId, setSecurityId] = useState("");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setError("");
    if (!securityId || !quantity || !price) {
      setError("All fields are required.");
      return;
    }
    try {
      await trade.mutateAsync({
        security_id: securityId, side,
        quantity: parseFloat(quantity), price_inr: parseFloat(price),
      });
      onClose();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }} onClick={onClose}>
      <div className="card" style={{ width: 440, maxHeight: "90vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: 16 }}>Record Trade</h3>

        <div className="form-group">
          <label className="form-label">Security</label>
          <select className="form-input" value={securityId} onChange={e => setSecurityId(e.target.value)}>
            <option value="">Select...</option>
            {securities.map((s: Security) => (
              <option key={s.id} value={s.id}>{s.symbol} — {s.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Side</label>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className={`btn ${side === "buy" ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1 }}
              onClick={() => setSide("buy")}
            >BUY</button>
            <button
              className={`btn ${side === "sell" ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1, background: side === "sell" ? "var(--error)" : undefined }}
              onClick={() => setSide("sell")}
            >SELL</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="form-label">Quantity</label>
            <input className="form-input" type="number" min="0" step="1" value={quantity} onChange={e => setQuantity(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Price (INR)</label>
            <input className="form-input" type="number" min="0" step="0.01" value={price} onChange={e => setPrice(e.target.value)} />
          </div>
        </div>

        {quantity && price && (
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
            Trade value: {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(parseFloat(quantity) * parseFloat(price))}
          </div>
        )}

        {error && <p style={{ color: "var(--error)", fontSize: 13, marginBottom: 8 }}>{error}</p>}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={trade.isPending}>
            {trade.isPending ? "Recording..." : "Submit Trade"}
          </button>
        </div>
      </div>
    </div>
  );
}
