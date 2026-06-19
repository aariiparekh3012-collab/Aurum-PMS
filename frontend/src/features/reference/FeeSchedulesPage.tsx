import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { referenceApi, FeeSchedule } from "./api";
import { auth } from "../../lib/auth";
import { Card, Button, Toast } from "../../components/ui";

function AddFeeScheduleForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [mgmtFee, setMgmtFee] = useState("");
  const [perfFee, setPerfFee] = useState("");
  const [hwm, setHwm] = useState(false);
  const [hurdle, setHurdle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      referenceApi.createFeeSchedule({
        name,
        mgmt_fee_pct: Number(mgmtFee),
        perf_fee_pct: Number(perfFee) || 0,
        high_water_mark: hwm,
        hurdle_rate_pct: hurdle ? Number(hurdle) : undefined,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = name.trim() && Number(mgmtFee) >= 0;

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>New Fee Schedule</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">Schedule Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Standard PMS" />
        </div>
        <div>
          <label className="label">Management Fee (%)</label>
          <input className="input" type="number" min="0" step="0.01" value={mgmtFee} onChange={(e) => setMgmtFee(e.target.value)} placeholder="2.00" />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Performance Fee (%)</label>
          <input className="input" type="number" min="0" step="0.01" value={perfFee} onChange={(e) => setPerfFee(e.target.value)} placeholder="20.00" />
        </div>
        <div>
          <label className="label">Hurdle Rate (%, optional)</label>
          <input className="input" type="number" min="0" step="0.01" value={hurdle} onChange={(e) => setHurdle(e.target.value)} placeholder="8.00" />
        </div>
        <div>
          <label className="label">High Water Mark</label>
          <div style={{ marginTop: 8 }}>
            <label style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
              <div
                onClick={() => setHwm(!hwm)}
                style={{
                  width: 44, height: 24, borderRadius: 12,
                  background: hwm ? "linear-gradient(135deg, var(--gold), var(--gold-2))" : "var(--surface-2)",
                  border: hwm ? "none" : "1px solid var(--line)",
                  position: "relative", transition: "background .2s", cursor: "pointer",
                }}
              >
                <div style={{
                  width: 18, height: 18, borderRadius: 9,
                  background: hwm ? "#1a1305" : "var(--muted)",
                  position: "absolute", top: 3, left: hwm ? 23 : 3,
                  transition: "left .2s",
                }} />
              </div>
              <span style={{ fontSize: ".88rem" }}>{hwm ? "Enabled" : "Disabled"}</span>
            </label>
          </div>
        </div>
      </div>
      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Create Fee Schedule
      </Button>
    </Card>
  );
}

export function FeeSchedulesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ["fee-schedules"],
    queryFn: () => referenceApi.feeSchedules(),
  });

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Fee Schedules</h1>
          <p className="muted">Management and performance fee structures for PMS portfolios</p>
        </div>
        {isCompliance && !showForm && (
          <Button variant="primary" onClick={() => setShowForm(true)}>+ New Schedule</Button>
        )}
      </div>

      {showForm && (
        <AddFeeScheduleForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Fee schedule created.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["fee-schedules"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi"><span className="kpi__value">{schedules.length}</span><span className="kpi__label">Fee schedules</span></div>
        <div className="kpi"><span className="kpi__value">{schedules.filter((s: FeeSchedule) => s.high_water_mark).length}</span><span className="kpi__label">With HWM</span></div>
      </div>

      <Card>
        <h2 style={{ marginBottom: 16 }}>Schedules</h2>
        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : schedules.length === 0 ? (
          <div className="empty">No fee schedules defined yet. {isCompliance && "Create one to assign to portfolio accounts."}</div>
        ) : (
          <table className="table">
            <thead><tr><th>Name</th><th>Mgmt Fee</th><th>Perf Fee</th><th>Hurdle</th><th>HWM</th></tr></thead>
            <tbody>
              {schedules.map((s: FeeSchedule) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td className="mono">{s.mgmt_fee_pct}%</td>
                  <td className="mono">{s.perf_fee_pct}%</td>
                  <td className="mono">{s.hurdle_rate_pct != null ? s.hurdle_rate_pct + "%" : "—"}</td>
                  <td>
                    <span className={`badge badge--${s.high_water_mark ? "success" : "info"}`}>
                      {s.high_water_mark ? "Yes" : "No"}
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
