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
import { performanceApi, portfolioApi, referenceApi } from "../lib/api";
import { Card, KPI, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { PortfolioAccount, PerformanceReturn } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

const pctFmt = (n: number) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";

const PERIOD_ORDER = ["1M", "3M", "6M", "1Y", "3Y", "SI"];

export function PerformanceScreen() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const { data: accounts = [], refetch: refetchAccounts } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.listAccounts(),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.listStrategies(),
  });

  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const { data: summary, isLoading } = useQuery({
    queryKey: ["performance-summary", selectedAccount],
    queryFn: () => (selectedAccount ? performanceApi.summary(selectedAccount) : Promise.resolve(null)),
    enabled: !!selectedAccount,
  });

  const onRefresh = async () => {
    setRefreshing(true);
    await refetchAccounts();
    setRefreshing(false);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
    >
      <FadeIn>
        <Text style={styles.title}>Performance</Text>
        <Text style={styles.subtitle}>Valuations, returns & benchmark comparison</Text>
      </FadeIn>

      {/* Account selector */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Select Account</Text>
        {accounts.length === 0 ? (
          <Text style={styles.empty}>No portfolio accounts found.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {accounts.map((a: PortfolioAccount) => (
              <Pressable
                key={a.id}
                onPress={() => setSelectedAccount(a.id)}
                style={[styles.chip, selectedAccount === a.id && styles.chipActive]}
              >
                <Text style={[styles.chipCode, selectedAccount === a.id && { color: colors.gold }]}>
                  {a.account_code}
                </Text>
                <Text style={styles.chipStrat}>{stratMap[a.strategy_id] || ""}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </Card>

      {selectedAccount && isLoading && <Loading text="Loading performance data..." />}

      {selectedAccount && summary && (
        <>
          {/* KPIs */}
          <View style={styles.kpiRow}>
            <KPI value={inr(summary.latest_market_value_paise)} label="Market Value" />
            <KPI value={inr(summary.latest_cost_value_paise)} label="Cost Basis" />
          </View>
          <View style={styles.kpiRow}>
            <KPI
              value={inr(summary.unrealised_pnl_paise)}
              label="Unrealised P&L"
            />
            <KPI value={inr(summary.latest_cash_paise)} label="Cash" />
          </View>

          {/* Returns table */}
          <Card style={{ marginTop: spacing.md }}>
            <Text style={styles.sectionTitle}>Returns vs Benchmark</Text>
            {summary.returns.length === 0 ? (
              <Text style={styles.empty}>No return data recorded yet.</Text>
            ) : (
              <>
                {/* Header */}
                <View style={styles.tableHeader}>
                  <Text style={[styles.headerCell, { flex: 1 }]}>Period</Text>
                  <Text style={[styles.headerCell, { flex: 1, textAlign: "right" }]}>TWRR</Text>
                  <Text style={[styles.headerCell, { flex: 1, textAlign: "right" }]}>Bench</Text>
                  <Text style={[styles.headerCell, { flex: 1, textAlign: "right" }]}>Alpha</Text>
                </View>
                {PERIOD_ORDER
                  .map((p) => summary.returns.find((r: PerformanceReturn) => r.period === p))
                  .filter((r): r is PerformanceReturn => !!r)
                  .map((r) => {
                    const alpha = r.benchmark_pct != null ? r.twrr_pct - r.benchmark_pct : null;
                    return (
                      <View key={r.period} style={styles.tableRow}>
                        <Text style={[styles.cell, { flex: 1, ...font.semibold }]}>{r.period}</Text>
                        <Text style={[styles.cell, { flex: 1, textAlign: "right", color: r.twrr_pct >= 0 ? colors.success : colors.danger }]}>
                          {pctFmt(r.twrr_pct)}
                        </Text>
                        <Text style={[styles.cell, { flex: 1, textAlign: "right" }]}>
                          {r.benchmark_pct != null ? pctFmt(r.benchmark_pct) : "---"}
                        </Text>
                        <Text style={[styles.cell, { flex: 1, textAlign: "right", color: alpha != null && alpha >= 0 ? colors.success : colors.danger }]}>
                          {alpha != null ? pctFmt(alpha) : "---"}
                        </Text>
                      </View>
                    );
                  })}
              </>
            )}
          </Card>

          {/* Valuation history */}
          {summary.history.length > 0 && (
            <Card style={{ marginTop: spacing.md }}>
              <Text style={styles.sectionTitle}>Valuation History</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.headerCell, { flex: 1.2 }]}>Date</Text>
                <Text style={[styles.headerCell, { flex: 1, textAlign: "right" }]}>Market</Text>
                <Text style={[styles.headerCell, { flex: 1, textAlign: "right" }]}>Cash</Text>
              </View>
              {summary.history.slice(-10).map((s) => (
                <View key={s.id} style={styles.tableRow}>
                  <Text style={[styles.cell, { flex: 1.2 }]}>
                    {new Date(s.as_of).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}
                  </Text>
                  <Text style={[styles.cell, { flex: 1, textAlign: "right" }]}>{inr(s.market_value_paise)}</Text>
                  <Text style={[styles.cell, { flex: 1, textAlign: "right" }]}>{inr(s.cash_paise)}</Text>
                </View>
              ))}
            </Card>
          )}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.md },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.sm },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 20 },
  chip: {
    paddingVertical: 10, paddingHorizontal: 16, borderRadius: radius.md,
    backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.line,
  },
  chipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  chipCode: { ...font.semibold, fontSize: 14, color: colors.text },
  chipStrat: { ...font.regular, fontSize: 11, color: colors.muted, marginTop: 2 },
  tableHeader: {
    flexDirection: "row", paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  headerCell: { ...font.medium, fontSize: 12, color: colors.muted, textTransform: "uppercase" },
  tableRow: {
    flexDirection: "row", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  cell: { ...font.regular, fontSize: 13, color: colors.text },
});
