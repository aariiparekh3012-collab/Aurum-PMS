import { useState } from "react";
import { useClients, usePortfolios } from "../hooks/usePortfolio";
import type { Client, PortfolioAccount } from "../types";
import PortfolioDetail from "./PortfolioDetail";
import RecordTradeModal from "./RecordTradeModal";
import CapitalFlowModal from "./CapitalFlowModal";

export default function PortfolioDashboard() {
  const { data: clients = [], isLoading: loadingClients } = useClients();
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [showFlowModal, setShowFlowModal] = useState(false);

  const { data: accounts = [], isLoading: loadingAccounts } = usePortfolios(selectedClientId);

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>Portfolio Dashboard</h2>

      {/* Client selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
              Client
            </label>
            <select
              className="form-input"
              style={{ marginTop: 4, minWidth: 260 }}
              value={selectedClientId}
              onChange={(e) => { setSelectedClientId(e.target.value); setSelectedAccountId(""); }}
            >
              <option value="">Select a client...</option>
              {clients.map((c: Client) => (
                <option key={c.id} value={c.id}>
                  {c.full_name} ({c.client_code})
                </option>
              ))}
            </select>
          </div>

          {selectedClientId && (
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
                Portfolio Account
              </label>
              <select
                className="form-input"
                style={{ marginTop: 4, minWidth: 260 }}
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
              >
                <option value="">Select account...</option>
                {accounts.map((a: PortfolioAccount) => (
                  <option key={a.id} value={a.id}>
                    {a.account_code} — {a.status}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        {loadingClients && <p style={{ marginTop: 8, color: "var(--text-secondary)", fontSize: 13 }}>Loading clients...</p>}
        {selectedClientId && loadingAccounts && <p style={{ marginTop: 8, color: "var(--text-secondary)", fontSize: 13 }}>Loading accounts...</p>}
      </div>

      {/* Portfolio detail */}
      {selectedAccountId && (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            <button className="btn btn-primary" onClick={() => setShowTradeModal(true)}>
              Record Trade
            </button>
            <button className="btn btn-outline" onClick={() => setShowFlowModal(true)}>
              Capital Flow
            </button>
          </div>

          <PortfolioDetail accountId={selectedAccountId} />

          {showTradeModal && (
            <RecordTradeModal
              accountId={selectedAccountId}
              onClose={() => setShowTradeModal(false)}
            />
          )}
          {showFlowModal && (
            <CapitalFlowModal
              accountId={selectedAccountId}
              onClose={() => setShowFlowModal(false)}
            />
          )}
        </>
      )}

      {!selectedClientId && (
        <div className="card" style={{ textAlign: "center", padding: 48, color: "var(--text-secondary)" }}>
          Select a client above to view their portfolio accounts.
        </div>
      )}
    </div>
  );
}
