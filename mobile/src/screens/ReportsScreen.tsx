import React, { useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { reportsApi, portfolioApi, referenceApi } from "../lib/api";
import { Card, Button, KPI, Loading, Toast } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { PortfolioAccount, PortfolioStatement, TransactionReport, PerformanceReport, FeeInvoice } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

const pctFmt = (n: number) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";

type ReportKey = "portfolio_statement" | "transaction_report" | "performance_report" | "fee_invoice";

const REPORT_OPTIONS: { key: ReportKey; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "portfolio_statement", label: "Portfolio Statement", icon: "document-text-outline" },
  { key: "transaction_report", label: "Transactions", icon: "swap-horizontal-outline" },
  { key: "performance_report", label: "Performance", icon: "trending-up-outline" },
  { key: "fee_invoice", label: "Fee Invoice", icon: "receipt-outline" },
];

function today() { return new Date().toISOString().slice(0, 10); }
function thirtyDaysAgo() { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); }

export function ReportsScreen() {
  const [reportType, setReportType] = useState<ReportKey | null>(null);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const fromDate = thirtyDaysAgo();
  const toDate = today();

  const { data: accounts = [] } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.listAccounts(),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.listStrategies(),
  });

  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const { data: reportData, isLoading: loadingReport } = useQuery<any>({
    queryKey: ["report", reportType, accountId, trigger],
    queryFn: () => {
      if (!reportType || !accountId) return null;
      switch (reportType) {
        case "portfolio_statement": return reportsApi.portfolioStatement(accountId);
        case "transaction_report": return reportsApi.transactions(accountId, fromDate, toDate);
        case "performance_report": return reportsApi.performance(accountId);
        case "fee_invoice": return reportsApi.feeInvoice(accountId, fromDate, toDate);
      }
    },
    enabled: trigger > 0 && !!reportType && !!accountId,
  });

  const canGenerate = !!reportType && !!accountId;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      <FadeIn>
        <Text style={styles.title}>Reports</Text>
        <Text style={styles.subtitle}>Generate portfolio statements & fee invoices</Text>
      </FadeIn>

      {/* Report type selector */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Report Type</Text>
        <View style={styles.reportGrid}>
          {REPORT_OPTIONS.map((o) => (
            <Pressable
              key={o.key}
              onPress={() => { setReportType(o.key); setTrigger(0); }}
              style={[styles.reportChip, reportType === o.key && styles.reportChipActive]}
            >
              <Ionicons name={o.icon} size={20} color={reportType === o.key ? colors.gold : colors.muted} />
              <Text style={[styles.reportChipText, reportType === o.key && { color: colors.gold }]}>{o.label}</Text>
            </Pressable>
          ))}
        </View>
      </Card>

      {/* Account selector */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Portfolio Account</Text>
        {accounts.length === 0 ? (
          <Text style={styles.empty}>No accounts found.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {accounts.map((a: PortfolioAccount) => (
              <Pressable
                key={a.id}
                onPress={() => { setAccountId(a.id); setTrigger(0); }}
                style={[styles.acctChip, accountId === a.id && styles.acctChipActive]}
              >
                <Text style={[styles.acctCode, accountId === a.id && { color: colors.gold }]}>{a.account_code}</Text>
                <Text style={styles.acctStrat}>{stratMap[a.strategy_id] || ""}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </Card>

      {/* Generate button */}
      <Button
        variant="primary"
        disabled={!canGenerate}
        onPress={() => setTrigger((t) => t + 1)}
        style={{ marginBottom: spacing.lg }}
      >
        Generate Report
      </Button>

      {loadingReport && <Loading text="Generating report..." />}

      {/* ── Portfolio Statement ── */}
      {reportData && reportType === "portfolio_statement" && (() => {
        const d = reportData as PortfolioStatement;
        return (
          <Card>
            <Text style={styles.reportTitle}>{d.account_code} — {d.strategy_name}</Text>
            <Text style={styles.reportMeta}>As of {d.as_of} · Inception {d.inception_date}</Text>
            <View style={styles.kpiRow}>
              <KPI value={inr(d.market_value_paise)} label="Market Value" />
              <KPI value={inr(d.cost_value_paise)} label="Cost Basis" />
            </View>
            <View style={styles.kpiRow}>
              <KPI value={inr(d.unrealised_pnl_paise)} label="Unrealised P&L" />
              <KPI value={inr(d.cash_paise)} label="Cash" />
            </View>
            {d.holdings.length > 0 && (
              <>
                <Text style={[styles.sectionTitle, { marginTop: spacing.md }]}>Holdings ({d.holdings.length})</Text>
                {d.holdings.map((h) => (
                  <View key={h.security_isin} style={styles.tableRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cellBold}>{h.security_symbol}</Text>
                      <Text style={styles.cellMuted}>{h.sector || "—"}</Text>
                    </View>
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={styles.cellValue}>{h.quantity} × {inr(h.avg_cost_paise)}</Text>
                      <Text style={styles.cellMuted}>{h.weight_pct}%</Text>
                    </View>
                  </View>
                ))}
              </>
            )}
          </Card>
        );
      })()}

      {/* ── Transaction Report ── */}
      {reportData && reportType === "transaction_report" && (() => {
        const d = reportData as TransactionReport;
        return (
          <Card>
            <Text style={styles.reportTitle}>{d.account_code} — Transactions</Text>
            <Text style={styles.reportMeta}>{d.from_date} to {d.to_date} · {d.trade_count} trades</Text>
            <View style={styles.kpiRow}>
              <KPI value={inr(d.total_buy_value_paise)} label="Total Buys" />
              <KPI value={inr(d.total_sell_value_paise)} label="Total Sells" />
            </View>
            {d.trades.map((t, i) => (
              <View key={i} style={styles.tableRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cellBold}>{t.security_symbol}</Text>
                  <Text style={styles.cellMuted}>{t.traded_at.slice(0, 10)}</Text>
                </View>
                <View style={{ alignItems: "flex-end" }}>
                  <Text style={[styles.cellValue, { color: t.side === "BUY" ? colors.success : colors.danger }]}>
                    {t.side} {t.quantity}
                  </Text>
                  <Text style={styles.cellMuted}>{inr(t.value_paise)}</Text>
                </View>
              </View>
            ))}
          </Card>
        );
      })()}

      {/* ── Performance Report ── */}
      {reportData && reportType === "performance_report" && (() => {
        const d = reportData as PerformanceReport;
        return (
          <Card>
            <Text style={styles.reportTitle}>{d.account_code} — Performance</Text>
            <Text style={styles.reportMeta}>{d.strategy_name} · Inception {d.inception_date}</Text>
            <View style={styles.kpiRow}>
              <KPI value={inr(d.latest_market_value_paise)} label="Market Value" />
              <KPI value={inr(d.unrealised_pnl_paise)} label="P&L" />
            </View>
            {d.returns.length > 0 && (
              <>
                <Text style={[styles.sectionTitle, { marginTop: spacing.md }]}>Returns</Text>
                {d.returns.map((r) => (
                  <View key={r.period} style={styles.tableRow}>
                    <Text style={[styles.cellBold, { flex: 1 }]}>{r.period}</Text>
                    <Text style={[styles.cellValue, { flex: 1, textAlign: "right", color: r.twrr_pct >= 0 ? colors.success : colors.danger }]}>
                      {pctFmt(r.twrr_pct)}
                    </Text>
                    <Text style={[styles.cellMuted, { flex: 1, textAlign: "right" }]}>
                      {r.benchmark_pct != null ? pctFmt(r.benchmark_pct) : "—"}
                    </Text>
                  </View>
                ))}
              </>
            )}
          </Card>
        );
      })()}

      {/* ── Fee Invoice ── */}
      {reportData && reportType === "fee_invoice" && (() => {
        const d = reportData as FeeInvoice;
        return (
          <Card>
            <Text style={styles.reportTitle}>{d.account_code} — Fee Invoice</Text>
            <Text style={styles.reportMeta}>{d.strategy_name} · {d.period_from} to {d.period_to}</Text>
            <View style={styles.kpiRow}>
              <KPI value={inr(d.aum_paise)} label="AUM" />
              <KPI value={d.fee_schedule_name} label="Fee Schedule" />
            </View>
            {d.items.map((item, i) => (
              <View key={i} style={styles.tableRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cellBold}>{item.description}</Text>
                  <Text style={styles.cellMuted}>{item.rate_pct}% of {inr(item.basis_paise)}</Text>
                </View>
                <Text style={styles.cellValue}>{inr(item.amount_paise)}</Text>
              </View>
            ))}
            <View style={[styles.tableRow, { borderTopWidth: 2, borderTopColor: colors.gold }]}>
              <Text style={[styles.cellBold, { flex: 1 }]}>Grand Total (incl. GST)</Text>
              <Text style={[styles.cellBold, { color: colors.gold, fontSize: 16 }]}>{inr(d.grand_total_paise)}</Text>
            </View>
          </Card>
        );
      })()}

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.sm },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 20 },
  reportGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  reportChip: {
    flexDirection: "row", alignItems: "center", gap: 8,
    paddingVertical: 10, paddingHorizontal: 14, borderRadius: radius.md,
    backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.line,
  },
  reportChipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  reportChipText: { ...font.medium, fontSize: 13, color: colors.textSecondary },
  acctChip: {
    paddingVertical: 10, paddingHorizontal: 16, borderRadius: radius.md,
    backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.line,
  },
  acctChipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  acctCode: { ...font.semibold, fontSize: 14, color: colors.text },
  acctStrat: { ...font.regular, fontSize: 11, color: colors.muted, marginTop: 2 },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  reportTitle: { ...font.bold, fontSize: 18, color: colors.text },
  reportMeta: { ...font.regular, fontSize: 12, color: colors.muted, marginBottom: spacing.sm },
  tableRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  cellBold: { ...font.semibold, fontSize: 14, color: colors.text },
  cellValue: { ...font.medium, fontSize: 14, color: colors.text },
  cellMuted: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
});
