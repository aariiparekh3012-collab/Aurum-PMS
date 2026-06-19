import { useState } from "react";
import { useRecordCapitalFlow } from "../hooks/usePortfolio";

interface Props {
  accountId: string;
  onClose: () => void;
}

export default function CapitalFlowModal({ accountId, onClose }: Props) {
  const flow = useRecordCapitalFlow(accountId);
  const [flowType, setFlowType] = useState<"contribution" | "withdrawal">("contribution");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setError("");
    const val = parseFloat(amount);
    if (!val || val <= 0) { setError("Enter a valid amount."); return; }
    try {
      await flow.mutateAsync({ flow_type: flowType, amount_inr: val });
      onClose();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const fmt = (v: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }} onClick={onClose}>
      <div className="card" style={{ width: 400 }} onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: 16 }}>Record Capital Flow</h3>

        <div className="form-group">
          <label className="form-label">Type</label>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className={`btn ${flowType === "contribution" ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1 }}
              onClick={() => setFlowType("contribution")}
            >Contribution</button>
            <button
              className={`btn ${flowType === "withdrawal" ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1 }}
              onClick={() => setFlowType("withdrawal")}
            >Withdrawal</button>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Amount (INR)</label>
          <input className="form-input" type="number" min="0" step="0.01"
            value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="e.g. 5000000"
          />
          {amount && parseFloat(amount) > 0 && (
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
              {fmt(parseFloat(amount))}
            </div>
          )}
        </div>

        {error && <p style={{ color: "var(--error)", fontSize: 13, marginBottom: 8 }}>{error}</p>}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={flow.isPending}>
            {flow.isPending ? "Recording..." : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
