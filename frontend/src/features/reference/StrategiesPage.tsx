import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { referenceApi, Strategy, Benchmark } from "./api";
import { auth } from "../../lib/auth";
import { Card, Button, Toast } from "../../components/ui";

const APPROACHES = ["value", "growth", "balanced", "momentum", "quality", "thematic", "quantitative"];

function AddStrategyForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const { data: benchmarks = [] } = useQuery({ queryKey: ["benchmarks"], queryFn: () => referenceApi.benchmarks() });

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [approach, setApproach] = useState("balanced");
  const [benchmarkId, setBenchmarkId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      referenceApi.createStrategy({
        name,
        code,
        approach,
        benchmark_id: benchmarkId || undefined,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = name.trim() && code.trim() && approach;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>New Strategy</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Strategy Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Large Cap Value" />
        </div>
        <div>
          <label className="label">Code</label>
          <input className="input" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. LCV" />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Approach</label>
          <select className="input" value={approach} onChange={(e) => setApproach(e.target.value)}>
            {APPROACHES.map((a) => (
              <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Benchmark (optional)</label>
          <select className="input" value={benchmarkId} onChange={(e) => setBenchmarkId(e.target.value)}>
            <option value="">— None —</option>
            {benchmarks.map((b: Benchmark) => (
              <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
            ))}
          </select>
        </div>
      </div>
      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Create Strategy
      </Button>
    </Card>
  );
}

export function StrategiesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: strategies = [], isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.strategies(),
  });
  const { data: benchmarks = [] } = useQuery({ queryKey: ["benchmarks"], queryFn: () => referenceApi.benchmarks() });

  const bmMap = Object.fromEntries(benchmarks.map((b) => [b.id, b.name]));
  const approachCounts = strategies.reduce<Record<string, number>>((acc, s) => {
    acc[s.approach] = (acc[s.approach] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Strategies</h1>
          <p className="muted">Investment strategies for discretionary PMS portfolios</p>
        </div>
        {isCompliance && !showForm && (
          <Button variant="primary" onClick={() => setShowForm(true)}>+ New Strategy</Button>
        )}
      </div>

      {showForm && (
        <AddStrategyForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Strategy created.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["strategies"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi"><span className="kpi__value">{strategies.length}</span><span className="kpi__label">Total strategies</span></div>
        <div className="kpi"><span className="kpi__value">{strategies.filter((s) => s.is_active).length}</span><span className="kpi__label">Active</span></div>
        <div className="kpi"><span className="kpi__value">{Object.keys(approachCounts).length}</span><span className="kpi__label">Approaches</span></div>
      </div>

      <Card>
        <h2 style={{ marginBottom: 16 }}>Strategy Directory</h2>
        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : strategies.length === 0 ? (
          <div className="empty">No strategies defined yet. {isCompliance && "Seed reference data or create one manually."}</div>
        ) : (
          <table className="table">
            <thead><tr><th>Name</th><th>Code</th><th>Approach</th><th>Benchmark</th><th>Status</th></tr></thead>
            <tbody>
              {strategies.map((s: Strategy) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td className="mono">{s.code}</td>
                  <td style={{ textTransform: "capitalize" }}>{s.approach}</td>
                  <td>{s.benchmark_id ? bmMap[s.benchmark_id] || "—" : "—"}</td>
                  <td>
                    <span className={`badge badge--${s.is_active ? "success" : "danger"}`}>
                      {s.is_active ? "active" : "inactive"}
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
