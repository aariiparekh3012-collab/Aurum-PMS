import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { referenceApi, Broker } from "./api";
import { auth } from "../../lib/auth";
import { Card, Button, Toast } from "../../components/ui";

function AddBrokerForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [sebiRegNo, setSebiRegNo] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => referenceApi.createBroker({ name, sebi_reg_no: sebiRegNo }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = name.trim() && sebiRegNo.trim();

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>Add Broker</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Broker Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Zerodha" />
        </div>
        <div>
          <label className="label">SEBI Registration No.</label>
          <input className="input" value={sebiRegNo} onChange={(e) => setSebiRegNo(e.target.value.toUpperCase())} placeholder="e.g. INZ000031633" />
        </div>
      </div>
      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Add Broker
      </Button>
    </Card>
  );
}

export function BrokersPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: brokers = [], isLoading } = useQuery({
    queryKey: ["brokers"],
    queryFn: () => referenceApi.brokers(),
  });

  const activeCount = brokers.filter((b) => b.is_active).length;

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Brokers</h1>
          <p className="muted">SEBI-registered execution brokers</p>
        </div>
        {isCompliance && !showForm && (
          <Button variant="primary" onClick={() => setShowForm(true)}>+ Add Broker</Button>
        )}
      </div>

      {showForm && (
        <AddBrokerForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Broker added successfully.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["brokers"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi"><span className="kpi__value">{brokers.length}</span><span className="kpi__label">Total brokers</span></div>
        <div className="kpi"><span className="kpi__value" style={{ color: "var(--success)" }}>{activeCount}</span><span className="kpi__label">Active</span></div>
      </div>

      <Card>
        <h2 style={{ marginBottom: 16 }}>Broker Directory</h2>
        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : brokers.length === 0 ? (
          <div className="empty">No brokers registered. {isCompliance && "Seed reference data or add one manually."}</div>
        ) : (
          <table className="table">
            <thead><tr><th>Name</th><th>SEBI Reg. No.</th><th>Status</th></tr></thead>
            <tbody>
              {brokers.map((b: Broker) => (
                <tr key={b.id}>
                  <td style={{ fontWeight: 600 }}>{b.name}</td>
                  <td className="mono">{b.sebi_reg_no}</td>
                  <td>
                    <span className={`badge badge--${b.is_active ? "success" : "danger"}`}>
                      {b.is_active ? "active" : "inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </div>
  );
}
