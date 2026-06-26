import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  investorApi,
  PortfolioSummary,
  HoldingDetail,
  CashEntry,
  FeeEntry,
  DocumentInfo,
} from "./api";
import { Card, StatusBadge, SkeletonKPIs, SkeletonTable, KPI } from "../../components/ui";
import { DonutChart, AreaChart, palette } from "../../components/charts";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);

const inrCompact = (paise: number) => {
  const abs = Math.abs(paise / 100);
  if (abs >= 1e7) return (paise >= 0 ? "" : "-") + "₹" + (abs / 1e7).toFixed(2) + " Cr";
  if (abs >= 1e5) return (paise >= 0 ? "" : "-") + "₹" + (abs / 1e5).toFixed(2) + " L";
  return inr(paise);
};

const pnlColor = (v: number) => (v >= 0 ? "var(--success)" : "var(--danger)");
const pnlSign = (v: number) => (v >= 0 ? "+" : "");

type Tab = "holdings" | "performance" | "cash" | "fees" | "documents";

export function InvestorPortal() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("holdings");

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

  const { data: valHistory = [] } = useQuery({
    queryKey: ["investor-valuation", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.valuationHistory(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount && tab === "performance",
  });

  const { data: fees = [] } = useQuery({
    queryKey: ["investor-fees", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.fees(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount && tab === "fees",
  });

  const { data: documents = [] } = useQuery({
    queryKey: ["investor-documents"],
    queryFn: investorApi.documents,
    enabled: tab === "documents",
  });

  if (isLoading) {
    return (
      <div className="fade-in">
        <div style={{ marginBottom: 24 }}>
          <h1>Investor Portal</h1>
          <p className="muted">Loading your portfolio&hellip;</p>
        </div>
        <SkeletonKPIs count={4} />
        <div style={{ marginTop: 24 }}><SkeletonTable rows={5} cols={4} /></div>
      </div>
    );
  }

  /* ─── Not yet active: show onboarding tracker ─── */
  if (!dash?.profile) {
    return <OnboardingTracker dash={dash} />;
  }

  /* ─── Active investor portal ─── */
  const { profile, portfolios, total_invested_paise, total_market_value_paise, total_unrealised_pnl_paise, total_cash_paise, returns } = dash;

  // Sector allocation from holdings
  const sectorMap = new Map<string, number>();
  holdings.forEach((h) => {
    const sector = h.sector || "Other";
    sectorMap.set(sector, (sectorMap.get(sector) || 0) + h.market_value_paise);
  });
  const sectorData = Array.from(sectorMap.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, value], i) => ({ label, value: Math.round(value / 100), color: palette(i) }));

  const totalHoldingsMV = holdings.reduce((s, h) => s + h.market_value_paise, 0);

  const selectedPortfolio = portfolios.find((p: PortfolioSummary) => p.account_id === selectedAccount);

  // Period order for returns display
  const periodOrder = ["1M", "3M", "6M", "1Y", "3Y", "SI"];
  const sortedReturns = [...returns].sort(
    (a, b) => periodOrder.indexOf(a.period) - periodOrder.indexOf(b.period),
  );

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1>
          Welcome, <span className="gold">{profile.full_name}</span>
        </h1>
        <p className="muted">
          Client code: <span className="mono">{profile.client_code}</span> &middot;{" "}
          <span style={{ textTransform: "capitalize" }}>{profile.risk_category || "unrated"}</span> risk profile
        </p>
      </div>

      {/* KPI row — enhanced with market values */}
      <div className="kpis" style={{ marginBottom: 24 }}>
        <KPI
          value={<span style={{ fontSize: "1.2rem" }}>{inrCompact(total_market_value_paise)}</span>}
          label="Portfolio Value"
        />
        <KPI
          value={<span style={{ fontSize: "1.2rem" }}>{inrCompact(total_invested_paise)}</span>}
          label="Total Invested"
        />
        <KPI
          value={
            <span style={{ fontSize: "1.2rem", color: pnlColor(total_unrealised_pnl_paise) }}>
              {pnlSign(total_unrealised_pnl_paise)}{inrCompact(total_unrealised_pnl_paise)}
            </span>
          }
          label="Unrealised P&L"
        />
        <KPI
          value={<span style={{ fontSize: "1.2rem" }}>{inrCompact(total_cash_paise)}</span>}
          label="Cash Balance"
        />
      </div>

      {/* Returns bar — if available */}
      {sortedReturns.length > 0 && (
        <Card style={{ marginBottom: 24 }}>
          <h2 className="card__title" style={{ marginBottom: 16 }}>Performance Returns (TWRR)</h2>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            {sortedReturns.map((r) => (
              <div key={r.period} style={{ textAlign: "center", minWidth: 70 }}>
                <div style={{ fontSize: "1.15rem", fontWeight: 600, color: pnlColor(r.twrr_pct) }}>
                  {pnlSign(r.twrr_pct)}{r.twrr_pct.toFixed(2)}%
                </div>
                <div className="faint" style={{ fontSize: ".78rem", marginTop: 2 }}>{r.period}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Portfolio cards */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16, marginBottom: 24 }}
      >
        {portfolios.map((p: PortfolioSummary) => {
          const selected = selectedAccount === p.account_id;
          return (
            <Card
              key={p.account_id}
              style={{
                cursor: "pointer",
                border: selected ? "1px solid var(--color-gold)" : undefined,
                transition: "border .2s ease",
              }}
              onClick={() => { setSelectedAccount(p.account_id); setTab("holdings"); }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <strong className="mono">{p.account_code}</strong>
                <StatusBadge status={p.status} />
              </div>
              <div className="faint" style={{ marginBottom: 8 }}>{p.strategy_name}</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: ".85rem" }}>
                <div>
                  <div className="faint" style={{ fontSize: ".75rem" }}>Market Value</div>
                  <div style={{ fontWeight: 600 }}>{inrCompact(p.market_value_paise)}</div>
                </div>
                <div>
                  <div className="faint" style={{ fontSize: ".75rem" }}>Unrealised P&L</div>
                  <div style={{ fontWeight: 600, color: pnlColor(p.unrealised_pnl_paise) }}>
                    {pnlSign(p.unrealised_pnl_paise)}{inrCompact(p.unrealised_pnl_paise)}
                  </div>
                </div>
                <div>
                  <div className="faint" style={{ fontSize: ".75rem" }}>Cash</div>
                  <div>{inrCompact(p.cash_balance_paise)}</div>
                </div>
                <div>
                  <div className="faint" style={{ fontSize: ".75rem" }}>Positions</div>
                  <div>{p.holdings_count}</div>
                </div>
              </div>
              <div className="faint" style={{ fontSize: ".75rem", marginTop: 8 }}>
                Since {new Date(p.inception_date).toLocaleDateString("en-IN")}
              </div>
            </Card>
          );
        })}
      </div>

      {portfolios.length === 0 && (
        <Card>
          <div className="empty">
            No portfolio accounts yet. Your relationship manager will set these up for you.
          </div>
        </Card>
      )}

      {/* Tab content area */}
      {(selectedAccount || tab === "documents") && (
        <Card>
          <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
            {(["holdings", "performance", "cash", "fees", "documents"] as const).map((t) => (
              <button
                key={t}
                className={`btn btn--sm ${tab === t ? "btn--primary" : "btn--ghost"}`}
                onClick={() => setTab(t)}
              >
                {t === "holdings" ? "Holdings" : t === "performance" ? "Performance" : t === "cash" ? "Cash Ledger" : t === "fees" ? "Fee History" : "Documents"}
              </button>
            ))}
            {selectedPortfolio && (
              <span className="mono faint" style={{ fontSize: ".82rem", marginLeft: "auto" }}>
                {selectedPortfolio.account_code}
              </span>
            )}
          </div>

          {/* ── Holdings tab ── */}
          {tab === "holdings" && selectedAccount && (
            <>
              {loadingHoldings ? (
                <SkeletonTable rows={5} cols={8} />
              ) : holdings.length === 0 ? (
                <div className="empty">No holdings in this account.</div>
              ) : (
                <>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Security</th>
                        <th>Sector</th>
                        <th style={{ textAlign: "right" }}>Qty</th>
                        <th style={{ textAlign: "right" }}>Avg Cost</th>
                        <th style={{ textAlign: "right" }}>MKT Price</th>
                        <th style={{ textAlign: "right" }}>MKT Value</th>
                        <th style={{ textAlign: "right" }}>P&L</th>
                        <th style={{ textAlign: "right" }}>Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.map((h: HoldingDetail, i: number) => (
                        <tr key={i}>
                          <td>
                            <span className="mono" style={{ fontWeight: 600 }}>{h.security_symbol}</span>
                            <div className="faint" style={{ fontSize: ".75rem" }}>{h.security_isin}</div>
                          </td>
                          <td>{h.sector || "—"}</td>
                          <td style={{ textAlign: "right" }}>{h.quantity}</td>
                          <td style={{ textAlign: "right" }}>{inr(h.avg_cost_paise)}</td>
                          <td style={{ textAlign: "right" }}>{inr(h.market_price_paise)}</td>
                          <td style={{ textAlign: "right", fontWeight: 600 }}>{inr(h.market_value_paise)}</td>
                          <td style={{ textAlign: "right", color: pnlColor(h.unrealised_pnl_paise) }}>
                            {pnlSign(h.unrealised_pnl_paise)}{inr(h.unrealised_pnl_paise)}
                          </td>
                          <td style={{ textAlign: "right", color: "var(--gold)" }}>
                            {totalHoldingsMV > 0
                              ? ((h.market_value_paise / totalHoldingsMV) * 100).toFixed(1) + "%"
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="row row--between" style={{ marginTop: 12, padding: "8px 0", borderTop: "1px solid var(--line)" }}>
                    <span className="faint">Total ({holdings.length} positions)</span>
                    <div style={{ display: "flex", gap: 24 }}>
                      <span>Cost: <strong>{inrCompact(holdings.reduce((s, h) => s + h.cost_value_paise, 0))}</strong></span>
                      <span>Market: <strong>{inrCompact(totalHoldingsMV)}</strong></span>
                      <span style={{ color: pnlColor(totalHoldingsMV - holdings.reduce((s, h) => s + h.cost_value_paise, 0)) }}>
                        P&L: <strong>
                          {pnlSign(totalHoldingsMV - holdings.reduce((s, h) => s + h.cost_value_paise, 0))}
                          {inrCompact(totalHoldingsMV - holdings.reduce((s, h) => s + h.cost_value_paise, 0))}
                        </strong>
                      </span>
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Performance tab ── */}
          {tab === "performance" && selectedAccount && (
            <div className="grid" style={{ gridTemplateColumns: "2fr 1fr", gap: 24 }}>
              <div>
                <h3 style={{ marginBottom: 12, fontSize: ".95rem" }}>Portfolio Value Over Time</h3>
                {valHistory.length > 1 ? (
                  <AreaChart
                    data={valHistory.map((v) => ({ x: v.as_of, y: Math.round(v.market_value_paise / 100) }))}
                    height={220}
                    color={palette(0)}
                  />
                ) : (
                  <div className="empty" style={{ minHeight: 180 }}>
                    Valuation history will appear here after daily mark-to-market runs.
                  </div>
                )}
              </div>
              <div>
                <h3 style={{ marginBottom: 12, fontSize: ".95rem" }}>Sector Allocation</h3>
                {sectorData.length > 0 ? (
                  <DonutChart data={sectorData} size={180} />
                ) : (
                  <div className="empty">No sector data.</div>
                )}
                {holdings.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h3 style={{ marginBottom: 8, fontSize: ".95rem" }}>Top Holdings</h3>
                    <div style={{ display: "grid", gap: 6 }}>
                      {[...holdings]
                        .sort((a, b) => b.market_value_paise - a.market_value_paise)
                        .slice(0, 5)
                        .map((h, i) => {
                          const pct = totalHoldingsMV > 0 ? (h.market_value_paise / totalHoldingsMV) * 100 : 0;
                          return (
                            <div key={i}>
                              <div className="row row--between" style={{ marginBottom: 2 }}>
                                <span style={{ fontSize: ".82rem" }} className="mono">{h.security_symbol}</span>
                                <span className="faint" style={{ fontSize: ".78rem" }}>{pct.toFixed(1)}%</span>
                              </div>
                              <div style={{ height: 5, background: "var(--border-light)", borderRadius: 3, overflow: "hidden" }}>
                                <div style={{
                                  width: `${pct}%`, height: "100%", borderRadius: 3,
                                  background: `linear-gradient(90deg, ${palette(i)}dd, ${palette(i)})`,
                                  transition: "width .5s ease",
                                }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Cash Ledger tab ── */}
          {tab === "cash" && selectedAccount && (
            <>
              {loadingCash ? (
                <SkeletonTable rows={5} cols={4} />
              ) : cash.length === 0 ? (
                <div className="empty">No cash entries yet.</div>
              ) : (
                <>
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
                          <td style={{ textTransform: "capitalize" }}>{c.entry_type.replace(/_/g, " ")}</td>
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

          {/* ── Fee History tab ── */}
          {tab === "fees" && selectedAccount && (
            <>
              {fees.length === 0 ? (
                <div className="empty">No fees charged yet.</div>
              ) : (
                <>
                  <div style={{ marginBottom: 16, padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: 8 }}>
                    <div className="faint" style={{ fontSize: ".78rem" }}>Total fees charged</div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                      {inr(fees.reduce((s, f) => s + f.amount_paise, 0))}
                    </div>
                  </div>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Description</th>
                        <th style={{ textAlign: "right" }}>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fees.map((f: FeeEntry, i: number) => (
                        <tr key={i}>
                          <td>{new Date(f.posted_on).toLocaleDateString("en-IN")}</td>
                          <td>
                            <span className={`badge ${f.entry_type === "perf_fee" ? "badge--info" : f.entry_type === "exit_load" ? "badge--warning" : ""}`}>
                              {f.entry_type.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td>{f.description}</td>
                          <td style={{ textAlign: "right", fontWeight: 500 }}>{inr(f.amount_paise)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </>
          )}

          {/* ── Documents tab ── */}
          {tab === "documents" && (
            <>
              {documents.length === 0 ? (
                <div className="empty">No documents uploaded yet.</div>
              ) : (
                <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
                  {documents.map((d: DocumentInfo) => (
                    <div
                      key={d.id}
                      style={{
                        padding: "16px",
                        background: "var(--bg-secondary)",
                        borderRadius: 8,
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      <div style={{ fontSize: "1.5rem", textAlign: "center" }}>
                        {d.document_type.includes("photo") ? "🖼" : "📄"}
                      </div>
                      <div style={{ fontWeight: 600, fontSize: ".88rem", textTransform: "capitalize", textAlign: "center" }}>
                        {d.document_type.replace(/_/g, " ")}
                      </div>
                      <div className="faint" style={{ fontSize: ".75rem", textAlign: "center" }}>
                        Uploaded {new Date(d.uploaded_at).toLocaleDateString("en-IN")}
                      </div>
                      {d.download_url && (
                        <a
                          href={d.download_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn--sm btn--ghost"
                          style={{ marginTop: "auto", textAlign: "center" }}
                        >
                          View
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
}

/* ─── Onboarding tracker (pre-active state) ─── */
function OnboardingTracker({ dash }: { dash: any }) {
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
