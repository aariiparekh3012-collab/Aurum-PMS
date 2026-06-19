import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { investorApi, PortfolioSummary, HoldingDetail, CashEntry } from "./api";
import { Card, StatusBadge, SkeletonKPIs, SkeletonTable } from "../../components/ui";
import { DonutChart, palette } from "../../components/charts";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);



export function InvestorPortal() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [tab, setTab] = useState<"holdings" | "performance" | "cash">("holdings");

  const { data: dash, isLoading } = useQuery({
    queryKey: ["investor-dashboard"],
    queryFn: investorApi.dashboard,
  });

  const { data: holdings = [], isLoading: loadingHoldings } = useQuery({
    queryKey: ["investor-holdings", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.holdings(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: cash = [], isLoading: loadingCash } = useQuery({
    queryKey: ["investor-cash", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.cash(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount && tab === "cash",
  });

  if (isLoading) {
    return (
      <div className="fade-in">
        <div style={{ marginBottom: 24 }}>
          <h1>Investor Portal</h1>
          <p className="muted">Loading your portfolio&hellip;</p>
        </div>
        <SkeletonKPIs count={3} />
        <div style={{ marginTop: 24 }}><SkeletonTable rows={5} cols={4} /></div>
      </div>
    );
  }

  // Not yet an active client
  if (!dash?.profile) {
    const ob = dash?.onboarding ?? null;
    const ORDER = [
      "draft", "kyc_pending", "kyc_verified", "risk_profiled",
      "agreement_pending", "agreement_signed", "under_review", "active",
    ];
    const idx = ob ? ORDER.indexOf(ob.status) : -1;
    const reached = (s: string) => idx >= 0 && idx >= ORDER.indexOf(s);
    const kycDone = reached("kyc_verified");
    const riskDone = reached("risk_profiled");
    const agreementSigned = reached("agreement_signed");
    const rejected = ob?.status === "kyc_rejected" || ob?.status === "rejected";

    const Pill = ({ done, label }: { done: boolean; label?: string }) => (
      <span className={`badge ${done ? "badge--success" : ""}`}>
        {label ?? (done ? "Completed" : "Pending")}
      </span>
    );

    const docs = [
      { name: "PAN Card", done: !!ob },
      { name: "Aadhaar / Identity (KYC)", done: kycDone },
      { name: "Bank Proof", done: kycDone },
      { name: "Demat (CMR)", done: kycDone },
      { name: "PMS Agreement", done: agreementSigned },
    ];

    return (
      <div className="fade-in" style={{ maxWidth: 760, margin: "0 auto" }}>
        <div style={{ marginBottom: 20 }}>
          <h1>My Onboarding</h1>
          <p className="muted">Track your KYC, risk profile, documents and agreement status.</p>
        </div>

        {!ob ? (
          <Card>
            <div className="empty">
              No onboarding application found for your account.<br />
              Please <a href="/onboarding">start your onboarding</a> or contact your relationship manager.
            </div>
          </Card>
        ) : (
          <>
            <Card style={{ marginBottom: 16 }}>
              <div className="row row--between">
                <div>
                  <strong>{ob.full_name}</strong>
                  <div className="faint" style={{ fontSize: ".82rem" }}>
                    Application {ob.id.slice(0, 8)}
                  </div>
                </div>
                <StatusBadge status={ob.status} />
              </div>
            </Card>

            <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Card>
                <h3 className="card__title">My KYC</h3>
                <div className="row row--between" style={{ marginBottom: 8 }}>
                  <span className="faint">Status</span>
                  <Pill done={kycDone} label={rejected ? "Rejected" : kycDone ? "Verified" : "In progress"} />
                </div>
                <div className="row row--between" style={{ marginBottom: 8 }}>
                  <span className="faint">PAN</span><span className="mono">{ob.pan}</span>
                </div>
                <div className="row row--between">
                  <span className="faint">Source</span>
                  <span style={{ textTransform: "uppercase" }}>{ob.kyc_source ?? "—"}</span>
                </div>
              </Card>

              <Card>
                <h3 className="card__title">My Risk Profile</h3>
                <div className="row row--between" style={{ marginBottom: 8 }}>
                  <span className="faint">Status</span>
                  <Pill done={riskDone} />
                </div>
                <div className="row row--between">
                  <span className="faint">Category</span>
                  {ob.risk_category ? (
                    <span className="badge badge--info" style={{ textTransform: "capitalize" }}>
                      {ob.risk_category}
                    </span>
                  ) : (
                    <span className="faint">Not assessed</span>
                  )}
                </div>
              </Card>

              <Card>
                <h3 className="card__title">My Documents</h3>
                <div style={{ display: "grid", gap: 8 }}>
                  {docs.map((d) => (
                    <div key={d.name} className="row row--between">
                      <span>{d.name}</span>
                      <Pill done={d.done} label={d.done ? "Received" : "Pending"} />
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <h3 className="card__title">Agreement Status</h3>
                <div className="row row--between" style={{ marginBottom: 8 }}>
                  <span className="faint">PMS Agreement</span>
                  <Pill done={agreementSigned} label={agreementSigned ? "Signed" : "Awaiting e-sign"} />
                </div>
                <div className="row row--between">
                  <span className="faint">Proposed investment</span>
                  <span>
                    {new Intl.NumberFormat("en-IN", {
                      style: "currency", currency: "INR", maximumFractionDigits: 0,
                    }).format(ob.proposed_investment_inr)}
                  </span>
                </div>
                {!agreementSigned && (
                  <p className="faint" style={{ fontSize: ".78rem", marginTop: 10, marginBottom: 0 }}>
                    Complete the agreement step in your onboarding to activate your PMS account.
                  </p>
                )}
              </Card>
            </div>
          </>
        )}
      </div>
    );
  }

  // Active client — full portal
  const { profile, portfolios, total_invested_paise } = dash;

  const sectorMap = new Map<string, number>();
  holdings.forEach((h) => {
    const sector = h.sector || "Other";
    sectorMap.set(sector, (sectorMap.get(sector) || 0) + h.cost_value_paise);
  });
  const sectorData = Array.from(sectorMap.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, value], i) => ({ label, value: Math.round(value / 100), color: palette(i) }));

  const totalHoldingsValue = holdings.reduce((s, h) => s + h.cost_value_paise, 0);
  const selectedPortfolio = portfolios.find((p: PortfolioSummary) => p.account_id === selectedAccount);

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>Welcome, {profile.full_name}</h1>
        <p className="muted">
          Client code: <span className="mono">{profile.client_code}</span> &middot;{" "}
          <span style={{ textTransform: "capitalize" }}>{profile.risk_category || "unrated"}</span> risk profile
        </p>
      </div>

      <div className="kpis" style={{ marginBottom: 24 }}>
        <div className="kpi">
          <span className="kpi__value">{portfolios.length}</span>
          <span className="kpi__label">Portfolios</span>
        </div>
        <div className="kpi">
          <span className="kpi__value">
            {portfolios.reduce((s: number, p: PortfolioSummary) => s + p.holdings_count, 0)}
          </span>
          <span className="kpi__label">Total positions</span>
        </div>
        <div className="kpi">
          <span className="kpi__value">{inr(total_invested_paise)}</span>
          <span className="kpi__label">Total invested</span>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 24 }}>
        {portfolios.map((p: PortfolioSummary) => (
          <Card
            key={p.account_id}
            style={{
              cursor: "pointer",
              border: selectedAccount === p.account_id ? "1px solid var(--color-gold)" : undefined,
              transition: "border .2s ease",
            }}
            onClick={() => { setSelectedAccount(p.account_id); setTab("holdings"); }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <strong className="mono">{p.account_code}</strong>
              <StatusBadge status={p.status} />
            </div>
            <div className="faint" style={{ marginBottom: 4 }}>{p.strategy_name}</div>
            <div style={{ fontSize: ".85rem" }}>
              {p.holdings_count} positions &middot; {inr(p.total_cost_paise)}
            </div>
            <div className="faint" style={{ fontSize: ".78rem", marginTop: 4 }}>
              Since {new Date(p.inception_date).toLocaleDateString("en-IN")}
            </div>
          </Card>
        ))}
      </div>

      {portfolios.length === 0 && (
        <Card>
          <div className="empty">
            No portfolio accounts yet. Your relationship manager will set these up for you.
          </div>
        </Card>
      )}

      {selectedAccount && (
        <>
          <Card style={{ marginBottom: 24 }}>
            <div className="row row--between" style={{ marginBottom: 16 }}>
              <div className="row" style={{ gap: 8 }}>
                {(["holdings", "performance", "cash"] as const).map((t) => (
                  <button
                    key={t}
                    className={`btn btn--sm ${tab === t ? "btn--primary" : "btn--ghost"}`}
                    onClick={() => setTab(t)}
                  >
                    {t === "holdings" ? "Holdings" : t === "performance" ? "Performance" : "Cash Ledger"}
                  </button>
                ))}
              </div>
              {selectedPortfolio && (
                <span className="mono faint" style={{ fontSize: ".82rem" }}>
                  {selectedPortfolio.account_code}
                </span>
              )}
            </div>

            {tab === "holdings" && (
              <>
                {loadingHoldings ? (
                  <SkeletonTable rows={5} cols={6} />
                ) : holdings.length === 0 ? (
                  <div className="empty">No holdings in this account.</div>
                ) : (
                  <>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Security</th>
                          <th>ISIN</th>
                          <th>Sector</th>
                          <th style={{ textAlign: "right" }}>Qty</th>
                          <th style={{ textAlign: "right" }}>Avg cost</th>
                          <th style={{ textAlign: "right" }}>Value</th>
                          <th style={{ textAlign: "right" }}>Weight</th>
                        </tr>
                      </thead>
                      <tbody>
                        {holdings.map((h: HoldingDetail, i: number) => (
                          <tr key={i}>
                            <td className="mono" style={{ fontWeight: 600 }}>{h.security_symbol}</td>
                            <td className="mono" style={{ fontSize: ".82rem" }}>{h.security_isin}</td>
                            <td>{h.sector || "—"}</td>
                            <td style={{ textAlign: "right" }}>{h.quantity}</td>
                            <td style={{ textAlign: "right" }}>{inr(h.avg_cost_paise)}</td>
                            <td style={{ textAlign: "right" }}>{inr(h.cost_value_paise)}</td>
                            <td style={{ textAlign: "right", color: "var(--gold)" }}>
                              {totalHoldingsValue > 0
                                ? ((h.cost_value_paise / totalHoldingsValue) * 100).toFixed(1) + "%"
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="row row--between" style={{ marginTop: 12, padding: "8px 0", borderTop: "1px solid var(--line)" }}>
                      <span className="faint">Total ({holdings.length} positions)</span>
                      <strong>{inr(totalHoldingsValue)}</strong>
                    </div>
                  </>
                )}
              </>
            )}

            {tab === "performance" && (
              <div>
                {holdings.length === 0 ? (
                  <div className="empty">Add holdings to see performance data.</div>
                ) : (
                  <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                    <div>
                      <h3 style={{ marginBottom: 12, fontSize: ".95rem" }}>Sector Allocation</h3>
                      {sectorData.length > 0 ? (
                        <DonutChart data={sectorData} size={180} />
                      ) : (
                        <div className="empty">No sector data available.</div>
                      )}
                    </div>
                    <div>
                      <h3 style={{ marginBottom: 12, fontSize: ".95rem" }}>Holdings Distribution</h3>
                      <div style={{ display: "grid", gap: 8 }}>
                        {[...holdings]
                          .sort((a, b) => b.cost_value_paise - a.cost_value_paise)
                          .slice(0, 8)
                          .map((h, i) => {
                            const pct = totalHoldingsValue > 0 ? (h.cost_value_paise / totalHoldingsValue) * 100 : 0;
                            return (
                              <div key={i}>
                                <div className="row row--between" style={{ marginBottom: 2 }}>
                                  <span style={{ fontSize: ".82rem" }} className="mono">{h.security_symbol}</span>
                                  <span className="faint" style={{ fontSize: ".78rem" }}>{pct.toFixed(1)}%</span>
                                </div>
                                <div style={{ height: 6, background: "var(--border-light)", borderRadius: 3, overflow: "hidden" }}>
                                  <div style={{
                                    width: `${pct}%`,
                                    height: "100%",
                                    borderRadius: 3,
                                    background: `linear-gradient(90deg, ${palette(i)}dd, ${palette(i)})`,
                                    transition: "width .5s ease",
                                  }} />
                                </div>
                              </div>
                            );
                          })}
                      </div>
                      {holdings.length > 8 && (
                        <p className="faint" style={{ marginTop: 8, fontSize: ".78rem" }}>
                          + {holdings.length - 8} more positions
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {tab === "cash" && (
              <>
                {loadingCash ? (
                  <SkeletonTable rows={5} cols={4} />
                ) : cash.length === 0 ? (
                  <div className="empty">No cash entries yet.</div>
                ) : (
                  <>
                    {cash.length > 0 && (
                      <div className="row" style={{ gap: 24, marginBottom: 16, padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: 8 }}>
                        <div>
                          <div className="faint" style={{ fontSize: ".78rem" }}>Current balance</div>
                          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>{inr(cash[0].balance_paise)}</div>
                        </div>
                        <div>
                          <div className="faint" style={{ fontSize: ".78rem" }}>Total entries</div>
                          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>{cash.length}</div>
                        </div>
                      </div>
                    )}
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Type</th>
                          <th style={{ textAlign: "right" }}>Amount</th>
                          <th style={{ textAlign: "right" }}>Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cash.map((c: CashEntry, i: number) => (
                          <tr key={i}>
                            <td>{new Date(c.posted_on).toLocaleDateString("en-IN")}</td>
                            <td style={{ textTransform: "capitalize" }}>
                              {c.entry_type.replace(/_/g, " ")}
                            </td>
                            <td style={{ textAlign: "right", color: c.amount_paise >= 0 ? "var(--success)" : "var(--danger)" }}>
                              {inr(c.amount_paise)}
                            </td>
                            <td style={{ textAlign: "right" }}>{inr(c.balance_paise)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
