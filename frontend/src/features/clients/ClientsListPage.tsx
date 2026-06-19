import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clientsApi } from "./api";
import { auth } from "../../lib/auth";
import { Button, Card, KPI, StatusBadge, SkeletonTable, SkeletonKPIs, useToast } from "../../components/ui";
import { DonutChart, BarChart, palette, type Slice } from "../../components/charts";

export function ClientsListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const isCompliance = auth.getUser()?.role === "compliance";

  const { data: clients = [], isLoading, error } = useQuery({
    queryKey: ["clients"],
    queryFn: clientsApi.list,
  });

  const provision = useMutation({
    mutationFn: clientsApi.processOutbox,
    onSuccess: (r) => {
      toast.success(`Provisioned ${r.processed} pending client(s).`);
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return clients.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.pan.toLowerCase().includes(q) ||
        c.client_code.toLowerCase().includes(q)
    );
  }, [clients, search]);

  const activeCount = clients.filter((c) => c.status === "active").length;
  const riskCounts = clients.reduce<Record<string, number>>((acc, c) => {
    if (c.risk_category) acc[c.risk_category] = (acc[c.risk_category] ?? 0) + 1;
    return acc;
  }, {});
  const topRisk = Object.entries(riskCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  const riskData: Slice[] = Object.entries(riskCounts).map(([label, value], i) => ({
    label, value, color: palette(i),
  }));
  const typeCounts = clients.reduce<Record<string, number>>((acc, c) => {
    acc[c.investor_type] = (acc[c.investor_type] ?? 0) + 1;
    return acc;
  }, {});
  const typeData: Slice[] = Object.entries(typeCounts).map(([label, value], i) => ({
    label, value, color: palette(i),
  }));

  return (
    <div>
      <div className="row row--between" style={{ marginBottom: 20 }}>
        <div>
          <h1>Clients</h1>
          <p className="muted">Onboarded discretionary PMS investors</p>
        </div>
        {isCompliance && (
          <Button variant="primary" loading={provision.isPending} onClick={() => provision.mutate()}>
            Provision pending
          </Button>
        )}
      </div>

      {isLoading ? (
        <SkeletonKPIs count={3} />
      ) : (
        <div className="kpis" style={{ marginBottom: 24 }}>
          <KPI value={clients.length} label="Total clients" />
          <KPI value={activeCount} label="Active accounts" />
          <KPI value={<span style={{ textTransform: "capitalize" }}>{topRisk}</span>} label="Top risk profile" />
        </div>
      )}

      {clients.length > 0 && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 24 }}>
          <Card>
            <h2 className="card__title">Risk distribution</h2>
            {riskData.length ? <DonutChart data={riskData} /> : <p className="faint">No risk data.</p>}
          </Card>
          <Card>
            <h2 className="card__title">Investor types</h2>
            <BarChart data={typeData} />
          </Card>
        </div>
      )}

      <Card>
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <h2>Directory</h2>
          <input
            className="input"
            style={{ maxWidth: 260 }}
            placeholder="Search name, PAN, code&hellip;"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {isLoading ? (
          <SkeletonTable rows={6} cols={6} />
        ) : error ? (
          <div className="empty">Could not load clients. {(error as Error).message}</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            No clients yet. Onboard one, then click <strong>Provision pending</strong>.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Client code</th><th>Name</th><th>PAN</th>
                <th>Type</th><th>Risk</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} onClick={() => navigate(`/clients/${c.id}`)}>
                  <td className="mono">{c.client_code}</td>
                  <td>{c.full_name}</td>
                  <td className="mono">{c.pan}</td>
                  <td style={{ textTransform: "capitalize" }}>{c.investor_type}</td>
                  <td style={{ textTransform: "capitalize" }}>{c.risk_category ?? "—"}</td>
                  <td><StatusBadge status={c.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
