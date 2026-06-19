import React, { useMemo, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import { Card, KPI, StatusBadge, Loading } from "../components/ui";
import { clientsApi } from "../lib/api";
import { colors, font, spacing, radius } from "../lib/theme";

export function ClientsListScreen() {
  const nav = useNavigation<any>();
  const [search, setSearch] = useState("");

  const { data: clients = [], isLoading, refetch } = useQuery({
    queryKey: ["clients"],
    queryFn: clientsApi.list,
  });
  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = async () => { setRefreshing(true); await refetch(); setRefreshing(false); };

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

  if (isLoading) return <Loading text="Loading clients..." />;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Clients</Text>
        <Text style={styles.subtitle}>Onboarded PMS investors</Text>
      </View>

      <View style={styles.kpiRow}>
        <KPI value={clients.length} label="Total" />
        <KPI value={activeCount} label="Active" />
      </View>

      <TextInput
        style={styles.searchInput}
        placeholder="Search name, PAN, code..."
        placeholderTextColor={colors.muted}
        value={search}
        onChangeText={setSearch}
        selectionColor={colors.gold}
      />

      <FlatList
        data={filtered}
        keyExtractor={(c) => c.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>
            {clients.length === 0 ? "No clients yet." : "No matches."}
          </Text>
        }
        renderItem={({ item: c }) => (
          <Card
            style={styles.clientCard}
            onPress={() => nav.navigate("ClientDetail", { id: c.id })}
          >
            <View style={styles.row}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{c.full_name[0]}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.clientName}>{c.full_name}</Text>
                <Text style={styles.clientCode}>{c.client_code} · {c.pan}</Text>
              </View>
              <View style={{ alignItems: "flex-end", gap: 4 }}>
                <StatusBadge status={c.status} />
                <Text style={styles.riskText}>{c.risk_category ?? "—"}</Text>
              </View>
            </View>
          </Card>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  header: { marginTop: spacing.sm, marginBottom: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
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
  clientCard: { marginBottom: spacing.sm },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { ...font.bold, fontSize: 18, color: colors.gold },
  clientName: { ...font.semibold, fontSize: 15, color: colors.text },
  clientCode: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  riskText: { ...font.regular, fontSize: 12, color: colors.textSecondary, textTransform: "capitalize" },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
});
