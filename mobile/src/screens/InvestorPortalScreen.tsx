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
import { investorApi } from "../lib/api";
import { Card, KPI, StatusBadge, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { PortfolioSummary, HoldingDetail, CashEntry } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (paise: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);

type DetailTab = "holdings" | "cash";

export function InvestorPortalScreen() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("holdings");
  const [refreshing, setRefreshing] = useState(false);

  const { data: dashboard, isLoading, refetch } = useQuery({
    queryKey: ["investor-dashboard"],
    queryFn: () => investorApi.dashboard(),
  });

  const { data: holdings = [] } = useQuery({
    queryKey: ["investor-holdings", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.holdings(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const { data: cash = [] } = useQuery({
    queryKey: ["investor-cash", selectedAccount],
    queryFn: () => (selectedAccount ? investorApi.cash(selectedAccount) : Promise.resolve([])),
    enabled: !!selectedAccount,
  });

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  if (isLoading) return <Loading text="Loading your portfolio..." />;

  const profile = dashboard?.profile;
  const onboarding = dashboard?.onboarding;
  const portfolios = dashboard?.portfolios || [];

  // Show onboarding status if not yet a client
  if (!profile && onboarding) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
        <FadeIn>
          <Text style={styles.title}>Welcome, {onboarding.full_name}</Text>
          <Text style={styles.subtitle}>Your onboarding is in progress</Text>
        </FadeIn>
        <Card style={{ marginTop: spacing.md }}>
          <View style={styles.onboardRow}>
            <Ionicons name="document-text-outline" size={24} color={colors.gold} />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.onboardLabel}>Application Status</Text>
              <StatusBadge status={onboarding.status} />
            </View>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>PAN</Text>
            <Text style={styles.infoValue}>{onboarding.pan}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Proposed Investment</Text>
            <Text style={styles.infoValue}>{inr(onboarding.proposed_investment_inr * 100)}</Text>
          </View>
        </Card>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
    >
      <FadeIn>
        <Text style={styles.title}>My Portfolio</Text>
        <Text style={styles.subtitle}>
          {profile ? `${profile.full_name} · ${profile.client_code}` : "Investor Dashboard"}
        </Text>
      </FadeIn>

      {/* KPIs */}
      <View style={styles.kpiRow}>
        <KPI value={portfolios.length} label="Accounts" />
        <KPI value={inr(dashboard?.total_invested_paise || 0)} label="Total Invested" />
      </View>

      {/* Portfolio cards */}
      {portfolios.length === 0 ? (
        <Card><Text style={styles.empty}>No portfolio accounts yet.</Text></Card>
      ) : (
        portfolios.map((p: PortfolioSummary) => (
          <Pressable
            key={p.account_id}
            onPress={() => setSelectedAccount(p.account_id)}
          >
            <Card style={[styles.portfolioCard, selectedAccount === p.account_id && styles.portfolioCardActive]}>
              <View style={styles.portfolioHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.acctCode}>{p.account_code}</Text>
                  <Text style={styles.stratName}>{p.strategy_name}</Text>
                </View>
                <StatusBadge status={p.status} />
              </View>
              <View style={styles.portfolioMeta}>
                <Text style={styles.metaItem}>{p.holdings_count} holdings</Text>
                <Text style={styles.metaItem}>Cost: {inr(p.total_cost_paise)}</Text>
                <Text style={styles.metaItem}>Since {p.inception_date}</Text>
              </View>
            </Card>
          </Pressable>
        ))
      )}

      {/* Detail view for selected account */}
      {selectedAccount && (
        <>
          <View style={styles.tabRow}>
            <Pressable onPress={() => setDetailTab("holdings")} style={[styles.tabBtn, detailTab === "holdings" && styles.tabBtnActive]}>
              <Ionicons name="bar-chart-outline" size={16} color={detailTab === "holdings" ? colors.gold : colors.muted} />
              <Text style={[styles.tabText, detailTab === "holdings" && styles.tabTextActive]}>Holdings</Text>
            </Pressable>
            <Pressable onPress={() => setDetailTab("cash")} style={[styles.tabBtn, detailTab === "cash" && styles.tabBtnActive]}>
              <Ionicons name="wallet-outline" size={16} color={detailTab === "cash" ? colors.gold : colors.muted} />
              <Text style={[styles.tabText, detailTab === "cash" && styles.tabTextActive]}>Cash</Text>
            </Pressable>
          </View>

          {detailTab === "holdings" ? (
            <Card>
              {holdings.length === 0 ? (
                <Text style={styles.empty}>No holdings in this account.</Text>
              ) : (
                holdings.map((h: HoldingDetail, i: number) => (
                  <View key={i} style={styles.holdingRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.holdingSymbol}>{h.security_symbol}</Text>
                      <Text style={styles.holdingSector}>{h.sector || "—"} · {h.security_isin}</Text>
                    </View>
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={styles.holdingQty}>{h.quantity} shares</Text>
                      <Text style={styles.holdingCost}>Cost: {inr(h.cost_value_paise)}</Text>
                    </View>
                  </View>
                ))
              )}
            </Card>
          ) : (
            <Card>
              {cash.length === 0 ? (
                <Text style={styles.empty}>No cash entries.</Text>
              ) : (
                cash.map((e: CashEntry, i: number) => (
                  <View key={i} style={styles.cashRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cashType}>{e.entry_type.replace(/_/g, " ")}</Text>
                      <Text style={styles.cashDate}>{new Date(e.posted_on).toLocaleDateString("en-IN")}</Text>
                    </View>
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={[styles.cashAmount, { color: e.amount_paise >= 0 ? colors.success : colors.danger }]}>
                        {e.amount_paise >= 0 ? "+" : ""}{inr(e.amount_paise)}
                      </Text>
                      <Text style={styles.cashBal}>Bal: {inr(e.balance_paise)}</Text>
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
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 20 },
  onboardRow: { flexDirection: "row", alignItems: "center", marginBottom: spacing.md },
  onboardLabel: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: 4 },
  infoRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line },
  infoLabel: { ...font.regular, fontSize: 13, color: colors.muted },
  infoValue: { ...font.medium, fontSize: 14, color: colors.text },
  portfolioCard: { marginBottom: spacing.sm },
  portfolioCardActive: { borderColor: colors.gold, borderWidth: 1 },
  portfolioHeader: { flexDirection: "row", alignItems: "flex-start", marginBottom: 8 },
  acctCode: { ...font.semibold, fontSize: 16, color: colors.text },
  stratName: { ...font.regular, fontSize: 12, color: colors.gold, marginTop: 2 },
  portfolioMeta: { flexDirection: "row", gap: spacing.md, flexWrap: "wrap" },
  metaItem: { ...font.regular, fontSize: 12, color: colors.muted },
  tabRow: { flexDirection: "row", gap: spacing.sm, marginVertical: spacing.md },
  tabBtn: {
    flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    paddingVertical: 12, borderRadius: radius.md, backgroundColor: colors.bgInput,
    borderWidth: 1, borderColor: colors.line,
  },
  tabBtnActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  tabText: { ...font.medium, fontSize: 14, color: colors.muted },
  tabTextActive: { color: colors.gold },
  holdingRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  holdingSymbol: { ...font.semibold, fontSize: 15, color: colors.text },
  holdingSector: { ...font.regular, fontSize: 11, color: colors.muted, marginTop: 2 },
  holdingQty: { ...font.medium, fontSize: 14, color: colors.text },
  holdingCost: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  cashRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  cashType: { ...font.medium, fontSize: 14, color: colors.text, textTransform: "capitalize" },
  cashDate: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  cashAmount: { ...font.semibold, fontSize: 15 },
  cashBal: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
});
