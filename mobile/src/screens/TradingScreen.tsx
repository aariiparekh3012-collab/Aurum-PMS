import React, { useState } from "react";
import {
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { tradingApi, referenceApi } from "../lib/api";
import { Card, Button, StatusBadge, Toast, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import { auth } from "../lib/auth";
import type { Order, Trade } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (paise: number | null) =>
  paise != null
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(paise / 100)
    : "—";

const ORDER_FILTERS = ["all", "pending_approval", "approved", "rejected", "filled"];
type Tab = "orders" | "trades";

export function TradingScreen() {
  const qc = useQueryClient();
  const isCompliance = auth.getUser()?.role === "compliance";
  const [tab, setTab] = useState<Tab>("orders");
  const [filter, setFilter] = useState("all");
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [tradeSearch, setTradeSearch] = useState("");

  // ── Orders ──
  const { data: orders = [], isLoading: loadingOrders, refetch: refetchOrders } = useQuery({
    queryKey: ["orders", filter],
    queryFn: () => tradingApi.listOrders(filter === "all" ? undefined : filter),
  });

  // ── Trades ──
  const { data: trades = [], isLoading: loadingTrades, refetch: refetchTrades } = useQuery({
    queryKey: ["trades"],
    queryFn: () => tradingApi.listTrades(),
  });

  // ── Reference ──
  const { data: securities = [] } = useQuery({ queryKey: ["securities"], queryFn: () => referenceApi.listSecurities() });
  const { data: strategies = [] } = useQuery({ queryKey: ["strategies"], queryFn: () => referenceApi.listStrategies() });
  const { data: brokers = [] } = useQuery({ queryKey: ["brokers"], queryFn: () => referenceApi.listBrokers() });

  const secMap = Object.fromEntries(securities.map((s) => [s.id, s.symbol]));
  const stratMap = Object.fromEntries(strategies.map((s) => [s.id, s.name]));
  const brokerMap = Object.fromEntries(brokers.map((b) => [b.id, b.name]));

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) => tradingApi.decideOrder(id, approve),
    onSuccess: (_, v) => {
      setToast({ msg: v.approve ? "Order approved." : "Order rejected.", variant: "success" });
      qc.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (e: Error) => setToast({ msg: e.message, variant: "error" }),
  });

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([refetchOrders(), refetchTrades()]);
    setRefreshing(false);
  };

  const filteredTrades = trades.filter((t) => {
    if (!tradeSearch) return true;
    return (secMap[t.security_id] || "").toLowerCase().includes(tradeSearch.toLowerCase());
  });

  return (
    <View style={styles.container}>
      <FadeIn>
        <Text style={styles.title}>Trading</Text>
        <Text style={styles.subtitle}>Orders & trade blotter</Text>
      </FadeIn>

      {/* Tab toggle */}
      <View style={styles.tabRow}>
        <Pressable onPress={() => setTab("orders")} style={[styles.tabBtn, tab === "orders" && styles.tabBtnActive]}>
          <Ionicons name="list-outline" size={16} color={tab === "orders" ? colors.gold : colors.muted} />
          <Text style={[styles.tabText, tab === "orders" && styles.tabTextActive]}>
            Orders ({orders.length})
          </Text>
        </Pressable>
        <Pressable onPress={() => setTab("trades")} style={[styles.tabBtn, tab === "trades" && styles.tabBtnActive]}>
          <Ionicons name="swap-horizontal-outline" size={16} color={tab === "trades" ? colors.gold : colors.muted} />
          <Text style={[styles.tabText, tab === "trades" && styles.tabTextActive]}>
            Trades ({trades.length})
          </Text>
        </Pressable>
      </View>

      {tab === "orders" ? (
        <>
          {/* Filter chips */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
            {ORDER_FILTERS.map((f) => (
              <Pressable key={f} onPress={() => setFilter(f)} style={[styles.chip, filter === f && styles.chipActive]}>
                <Text style={[styles.chipText, filter === f && styles.chipTextActive]}>{f.replace(/_/g, " ")}</Text>
              </Pressable>
            ))}
          </ScrollView>

          <FlatList
            data={orders}
            keyExtractor={(o) => o.id}
            contentContainerStyle={{ paddingBottom: 40 }}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
            ListEmptyComponent={
              loadingOrders
                ? <Loading text="Loading orders..." />
                : <Text style={styles.empty}>No orders in this view.</Text>
            }
            renderItem={({ item: o }) => (
              <Card style={styles.orderCard}>
                <View style={styles.orderTop}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.orderSymbol}>{secMap[o.security_id] || o.security_id.slice(0, 8)}</Text>
                    <Text style={styles.orderMeta}>{stratMap[o.strategy_id] || ""} · {o.order_type} · {o.quantity} qty</Text>
                  </View>
                  <View style={{ alignItems: "flex-end", gap: 4 }}>
                    <Text style={[styles.orderSide, { color: o.side === "buy" ? colors.success : colors.danger }]}>
                      {o.side.toUpperCase()}
                    </Text>
                    <StatusBadge status={o.status} />
                  </View>
                </View>
                {o.limit_price_paise && (
                  <Text style={styles.orderLimit}>Limit: {inr(o.limit_price_paise)}</Text>
                )}
                {o.status === "pending_approval" && isCompliance && (
                  <View style={styles.actions}>
                    <Button variant="primary" onPress={() => decide.mutate({ id: o.id, approve: true })}>Approve</Button>
                    <Button variant="danger" onPress={() => decide.mutate({ id: o.id, approve: false })}>Reject</Button>
                  </View>
                )}
              </Card>
            )}
          />
        </>
      ) : (
        <>
          <TextInput
            style={styles.searchInput}
            placeholder="Filter by symbol..."
            placeholderTextColor={colors.muted}
            value={tradeSearch}
            onChangeText={setTradeSearch}
            selectionColor={colors.gold}
          />
          <FlatList
            data={filteredTrades}
            keyExtractor={(t) => t.id}
            contentContainerStyle={{ paddingBottom: 40 }}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
            ListEmptyComponent={
              loadingTrades
                ? <Loading text="Loading trades..." />
                : <Text style={styles.empty}>No trades recorded.</Text>
            }
            renderItem={({ item: t }) => (
              <Card style={styles.orderCard}>
                <View style={styles.orderTop}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.orderSymbol}>{secMap[t.security_id] || t.security_id.slice(0, 8)}</Text>
                    <Text style={styles.orderMeta}>
                      {brokerMap[t.broker_id] || "—"} · {new Date(t.traded_at).toLocaleDateString("en-IN")}
                    </Text>
                  </View>
                  <View style={{ alignItems: "flex-end" }}>
                    <Text style={[styles.orderSide, { color: t.side === "buy" ? colors.success : colors.danger }]}>
                      {t.side.toUpperCase()}
                    </Text>
                    <Text style={styles.tradeValue}>{t.quantity} × {inr(t.price_paise)}</Text>
                  </View>
                </View>
                {t.contract_note && <Text style={styles.contractNote}>CN: {t.contract_note}</Text>}
              </Card>
            )}
          />
        </>
      )}

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
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
  filterRow: { gap: 8, paddingBottom: spacing.md },
  chip: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: radius.full,
    backgroundColor: colors.bgInput,
    borderWidth: 1,
    borderColor: colors.line,
  },
  chipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  chipText: { color: colors.textSecondary, fontSize: 13, ...font.medium, textTransform: "capitalize" },
  chipTextActive: { color: colors.gold },
  orderCard: { marginBottom: spacing.sm },
  orderTop: { flexDirection: "row", alignItems: "flex-start" },
  orderSymbol: { ...font.semibold, fontSize: 16, color: colors.text },
  orderMeta: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  orderSide: { ...font.bold, fontSize: 14 },
  orderLimit: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 6 },
  actions: { flexDirection: "row", gap: 10, marginTop: spacing.md },
  searchInput: {
    backgroundColor: colors.bgInput,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.line,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 15,
    marginBottom: spacing.md,
  },
  tradeValue: { ...font.medium, fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  contractNote: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 6 },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
});
