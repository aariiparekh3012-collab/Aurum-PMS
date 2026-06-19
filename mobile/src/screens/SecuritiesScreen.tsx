import React, { useState } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { referenceApi } from "../lib/api";
import { Card, Button, StatusBadge, KPI, Toast, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { Security } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

export function SecuritiesScreen() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);

  const { data: securities = [], isLoading, refetch } = useQuery({
    queryKey: ["securities", search],
    queryFn: () => referenceApi.listSecurities(search || undefined),
  });

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => referenceApi.listStrategies(),
  });

  const { data: brokers = [] } = useQuery({
    queryKey: ["brokers"],
    queryFn: () => referenceApi.listBrokers(),
  });

  const seed = useMutation({
    mutationFn: () => referenceApi.seed(),
    onSuccess: () => {
      setToast({ msg: "Reference data seeded.", variant: "success" });
      qc.invalidateQueries({ queryKey: ["securities"] });
      qc.invalidateQueries({ queryKey: ["strategies"] });
      qc.invalidateQueries({ queryKey: ["brokers"] });
    },
    onError: (e: Error) => setToast({ msg: e.message, variant: "error" }),
  });

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const activeSec = securities.filter((s) => s.is_active).length;

  return (
    <View style={styles.container}>
      <FadeIn>
        <Text style={styles.title}>Securities & Reference</Text>
        <Text style={styles.subtitle}>Browse securities, strategies & brokers</Text>
      </FadeIn>

      {/* KPIs */}
      <View style={styles.kpiRow}>
        <KPI value={securities.length} label="Securities" />
        <KPI value={strategies.length} label="Strategies" />
        <KPI value={brokers.length} label="Brokers" />
      </View>

      {/* Seed button */}
      <Button
        variant="ghost"
        onPress={() => seed.mutate()}
        style={{ marginBottom: spacing.md }}
      >
        Seed Reference Data
      </Button>

      {/* Search */}
      <TextInput
        style={styles.searchInput}
        placeholder="Search securities by symbol..."
        placeholderTextColor={colors.muted}
        value={search}
        onChangeText={setSearch}
        selectionColor={colors.gold}
        autoCapitalize="characters"
      />

      {/* Strategies & Brokers summary */}
      {strategies.length > 0 && (
        <Card style={{ marginBottom: spacing.sm }}>
          <Text style={styles.sectionTitle}>Strategies</Text>
          {strategies.map((s) => (
            <View key={s.id} style={styles.refRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.refName}>{s.name}</Text>
                <Text style={styles.refCode}>{s.code} · {s.approach}</Text>
              </View>
              <StatusBadge status={s.is_active ? "active" : "inactive"} />
            </View>
          ))}
        </Card>
      )}

      {brokers.length > 0 && (
        <Card style={{ marginBottom: spacing.sm }}>
          <Text style={styles.sectionTitle}>Brokers</Text>
          {brokers.map((b) => (
            <View key={b.id} style={styles.refRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.refName}>{b.name}</Text>
                <Text style={styles.refCode}>SEBI: {b.sebi_reg_no}</Text>
              </View>
              <StatusBadge status={b.is_active ? "active" : "inactive"} />
            </View>
          ))}
        </Card>
      )}

      {/* Securities list */}
      <FlatList
        data={securities}
        keyExtractor={(s) => s.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
        ListEmptyComponent={
          isLoading
            ? <Loading text="Loading securities..." />
            : <Text style={styles.empty}>No securities found.</Text>
        }
        renderItem={({ item: s }) => (
          <Card style={styles.secCard}>
            <View style={styles.secHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.secSymbol}>{s.symbol}</Text>
                <Text style={styles.secMeta}>{s.exchange} · {s.instrument_type}</Text>
              </View>
              <View style={{ alignItems: "flex-end", gap: 4 }}>
                <Text style={styles.secIsin}>{s.isin}</Text>
                <Text style={styles.secSector}>{s.sector || "—"}</Text>
              </View>
            </View>
          </Card>
        )}
      />

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.sm },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
  searchInput: {
    backgroundColor: colors.bgInput, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.line, color: colors.text,
    paddingHorizontal: spacing.md, paddingVertical: 12,
    fontSize: 15, marginBottom: spacing.md,
  },
  refRow: {
    flexDirection: "row", alignItems: "center", paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  refName: { ...font.semibold, fontSize: 14, color: colors.text },
  refCode: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  secCard: { marginBottom: spacing.sm },
  secHeader: { flexDirection: "row", alignItems: "flex-start" },
  secSymbol: { ...font.semibold, fontSize: 16, color: colors.text },
  secMeta: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  secIsin: { ...font.regular, fontSize: 12, color: colors.textSecondary, fontFamily: "monospace" },
  secSector: { ...font.regular, fontSize: 12, color: colors.muted },
});
