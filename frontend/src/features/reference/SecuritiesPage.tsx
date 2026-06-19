import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { referenceApi, Security } from "./api";
import { auth } from "../../lib/auth";
import { Button, Card, Toast } from "../../components/ui";

function AddSecurityForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [isin, setIsin] = useState("");
  const [symbol, setSymbol] = useState("");
  const [exchange, setExchange] = useState("NSE");
  const [instrumentType, setInstrumentType] = useState("equity");
  const [sector, setSector] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      referenceApi.createSecurity({
        isin: isin.toUpperCase(),
        symbol: symbol.toUpperCase(),
        exchange,
        instrument_type: instrumentType,
        sector: sector || undefined,
      }),
    onSuccess: () => onDone(),
    onError: (e: Error) => setError(e.message),
  });

  const valid = isin.trim().length >= 12 && symbol.trim();

  return (
    <Card style={{ marginBottom: 24 }}>
      <div className="row row--between" style={{ marginBottom: 16 }}>
        <h2>Add Security</h2>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {error && <div style={{ padding: 12, background: "rgba(248,113,113,.1)", borderRadius: 8, marginBottom: 16, color: "var(--danger)", fontSize: ".9rem" }}>{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label className="label">ISIN</label>
          <input className="input" value={isin} onChange={(e) => setIsin(e.target.value.toUpperCase())} placeholder="INE002A01018" maxLength={12} />
        </div>
        <div>
          <label className="label">Symbol</label>
          <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="RELIANCE" />
        </div>
        <div>
          <label className="label">Exchange</label>
          <select className="input" value={exchange} onChange={(e) => setExchange(e.target.value)}>
            <option value="NSE">NSE</option>
            <option value="BSE">BSE</option>
          </select>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label className="label">Instrument Type</label>
          <select className="input" value={instrumentType} onChange={(e) => setInstrumentType(e.target.value)}>
            <option value="equity">Equity</option>
            <option value="debt">Debt</option>
            <option value="etf">ETF</option>
            <option value="reit">REIT</option>
            <option value="invit">InvIT</option>
          </select>
        </div>
        <div>
          <label className="label">Sector (optional)</label>
          <input className="input" value={sector} onChange={(e) => setSector(e.target.value)} placeholder="e.g. Information Technology" />
        </div>
      </div>
      <Button variant="primary" disabled={!valid} loading={create.isPending} onClick={() => create.mutate()}>
        Add Security
      </Button>
    </Card>
  );
}

export function SecuritiesPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: securities = [], isLoading } = useQuery({
    queryKey: ["securities", search],
    queryFn: () => referenceApi.securities(search),
  });

  const seed = useMutation({
    mutationFn: referenceApi.seed,
    onSuccess: (r: any) => {
      setToast({
        msg: `Seeded ${r.securities} securities, ${r.strategies} strategies, ${r.brokers} brokers.`,
        variant: "success",
      });
      qc.invalidateQueries({ queryKey: ["securities"] });
      qc.invalidateQueries({ queryKey: ["strategies"] });
      qc.invalidateQueries({ queryKey: ["brokers"] });
    },
    onError: (e: Error) => setToast({ msg: e.message, variant: "error" }),
  });

  const sectors = securities.reduce<Record<string, number>>((acc, s) => {
    const key = s.sector || "Other";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const exchanges = securities.reduce<Record<string, number>>((acc, s) => {
    acc[s.exchange] = (acc[s.exchange] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Securities Master</h1>
          <p className="muted">NSE / BSE listed instruments</p>
        </div>
        {isCompliance && (
          <div className="row" style={{ gap: 8 }}>
            {!showForm && <Button variant="primary" onClick={() => setShowForm(true)}>+ Add Security</Button>}
            <Button variant="ghost" loading={seed.isPending} onClick={() => seed.mutate()}>
              Seed sample data
            </Button>
          </div>
        )}
      </div>

      {showForm && (
        <AddSecurityForm
          onDone={() => {
            setShowForm(false);
            setToast({ msg: "Security added.", variant: "success" });
            qc.invalidateQueries({ queryKey: ["securities"] });
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi">
          <span className="kpi__value">{securities.length}</span>
          <span className="kpi__label">Securities</span>
        </div>
        <div className="kpi">
          <span className="kpi__value">{Object.keys(sectors).length}</span>
          <span className="kpi__label">Sectors</span>
        </div>
        <div className="kpi">
          <span className="kpi__value">{Object.keys(exchanges).map((e) => e).join(" / ") || "—"}</span>
          <span className="kpi__label">Exchanges</span>
        </div>
      </div>

      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Browse</h2>
          <input
            className="input"
            style={{ maxWidth: 260 }}
            placeholder="Search symbol or ISIN..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading...</div>
        ) : securities.length === 0 ? (
          <div className="empty">
            No securities found.{" "}
            {isCompliance && (
              <span>
                Click <strong>Seed sample data</strong> to populate or <strong>+ Add Security</strong> to add manually.
              </span>
            )}
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>ISIN</th>
                <th>Exchange</th>
                <th>Type</th>
                <th>Sector</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {securities.map((s: Security) => (
                <tr key={s.id}>
                  <td className="mono" style={{ fontWeight: 600 }}>{s.symbol}</td>
                  <td className="mono">{s.isin}</td>
                  <td>{s.exchange}</td>
                  <td style={{ textTransform: "capitalize" }}>{s.instrument_type}</td>
                  <td>{s.sector || "—"}</td>
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
