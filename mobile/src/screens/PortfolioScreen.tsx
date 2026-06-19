import React, { useState } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { portfolioApi, referenceApi } from "../lib/api";
import { Card, KPI, StatusBadge, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { Holding, PortfolioAccount, CashLedgerEntry } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100);

type Tab = "holdings" | "cash";

export function PortfolioScreen() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("holdings");
  const [refreshing, setRefreshing] = useState(false);

  const { data: accounts = [], isLoading, refetch: refetchAccounts } = useQuery({
    queryKey: ["portfolio-accounts"],
    queryFn: () => portfolioApi.listAccounts(),
  });

  const { data: holdings = [], refetch: refetchHoldings } = useQuery({
    queryKey: ["holdings", selectedAccount],
    queryFn: () => (selectedAccount ? portfolioApi.listHoldings(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: cashLedger = [], refetch: refetchCash } = useQuery({
    queryKey: ["cash-ledger", selectedAccount],
    queryFn: () => (selectedAccount ? portfolioApi.listCashLedger(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: securities = [] } = useQuery({
    queryKey: ["securities"],
    queryFn: () => referenceApi.listSecurities(),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.listStrategies(),
  });

  const secMap = Object.fromEntries(securities.map((s) => [s.id, s]));
  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));

  const totalCost = holdings.reduce((sum, h) => sum + h.avg_cost_paise * h.quantity, 0);

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([refetchAccounts(), refetchHoldings(), refetchCash()]);
    setRefreshing(false);
  };

  if (isLoading) return <Loading text="Loading portfolio..." />;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
    >
      <FadeIn>
        <Text style={styles.title}>Portfolio</Text>
        <Text style={styles.subtitle}>Holdings & cash ledger</Text>
      </FadeIn>

      {/* KPIs */}
      <View style={styles.kpiRow}>
        <KPI value={accounts.length} label="Accounts" />
        <KPI value={holdings.length} label="Positions" />
        {totalCost > 0 && <KPI value={inr(totalCost)} label="Total cost" />}
      </View>

      {/* Account selector */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Select Account</Text>
        {accounts.length === 0 ? (
          <Text style={styles.empty}>No portfolio accounts yet.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {accounts.map((a: PortfolioAccount) => (
              <Pressable
                key={a.id}
                onPress={() => setSelectedAccount(a.id)}
                style={[styles.acctChip, selectedAccount === a.id && styles.acctChipActive]}
              >
                <Text style={[styles.acctCode, selectedAccount === a.id && { color: colors.gold }]}>
                  {a.account_code}
                </Text>
                <Text style={styles.acctStrategy}>{stratMap[a.strategy_id] || ""}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </Card>

      {selectedAccount && (
        <>
          {/* Tab toggle */}
          <View style={styles.tabRow}>
            <Pressable onPress={() => setTab("holdings")} style={[styles.tabBtn, tab === "holdings" && styles.tabBtnActive]}>
              <Ionicons name="bar-chart-outline" size={16} color={tab === "holdings" ? colors.gold : colors.muted} />
              <Text style={[styles.tabText, tab === "holdings" && styles.tabTextActive]}>Holdings</Text>
            </Pressable>
            <Pressable onPress={() => setTab("cash")} style={[styles.tabBtn, tab === "cash" && styles.tabBtnActive]}>
              <Ionicons name="wallet-outline" size={16} color={tab === "cash" ? colors.gold : colors.muted} />
              <Text style={[styles.tabText, tab === "cash" && styles.tabTextActive]}>Cash Ledger</Text>
            </Pressable>
          </View>

          {tab === "holdings" ? (
            <Card>
              <Text style={styles.sectionTitle}>Holdings</Text>
              {holdings.length === 0 ? (
                <Text style={styles.empty}>No holdings in this account.</Text>
              ) : (
                holdings.map((h: Holding) => {
                  const sec = secMap[h.security_id];
                  return (
                    <View key={h.id} style={styles.holdingRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.holdingSymbol}>{sec?.symbol || h.security_id.slice(0, 8)}</Text>
                        <Text style={styles.holdingSector}>{sec?.sector || "—"}</Text>
                      </View>
                      <View style={{ alignItems: "flex-end" }}>
                        <Text style={styles.holdingQty}>{h.quantity} shares</Text>
                        <Text style={styles.holdingCost}>Avg {inr(h.avg_cost_paise)}</Text>
                      </View>
                    </View>
                  );
                })
              )}
            </Card>
          ) : (
            <Card>
              <Text style={styles.sectionTitle}>Cash Ledger</Text>
              {cashLedger.length === 0 ? (
                <Text style={styles.empty}>No cash entries.</Text>
              ) : (
                cashLedger.map((e: CashLedgerEntry) => (
                  <View key={e.id} style={styles.cashRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cashType}>{e.entry_type.replace(/_/g, " ")}</Text>
                      <Text style={styles.cashDate}>{new Date(e.posted_on).toLocaleDateString("en-IN")}</Text>
                    </View>
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={[styles.cashAmount, { color: e.amount_paise >= 0 ? colors.success : colors.danger }]}>
                        {e.amount_paise >= 0 ? "+" : ""}{inr(e.amount_paise)}
                      </Text>
                      <Text style={styles.cashBalance}>Bal: {inr(e.balance_paise)}</Text>
                    </View>
                  </View>
                ))
              )}
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
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.md },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 20 },
  acctChip: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: radius.md,
    backgroundColor: colors.bgInput,
    borderWidth: 1,
    borderColor: colors.line,
  },
  acctChipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  acctCode: { ...font.semibold, fontSize: 14, color: colors.text },
  acctStrategy: { ...font.regular, fontSize: 11, color: colors.muted, marginTop: 2 },
  tabRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  tabBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
    borderRadius: radius.md,
    backgroundColor: colors.bgInput,
    borderWidth: 1,
    borderColor: colors.line,
  },
  tabBtnActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  tabText: { ...font.medium, fontSize: 14, color: colors.muted },
  tabTextActive: { color: colors.gold },
  holdingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  holdingSymbol: { ...font.semibold, fontSize: 15, color: colors.text },
  holdingSector: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  holdingQty: { ...font.medium, fontSize: 14, color: colors.text },
  holdingCost: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  cashRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  cashType: { ...font.medium, fontSize: 14, color: colors.text, textTransform: "capitalize" },
  cashDate: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  cashAmount: { ...font.semibold, fontSize: 15 },
  cashBalance: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
});
