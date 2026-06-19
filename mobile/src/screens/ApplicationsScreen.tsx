import React, { useState } from "react";
import {
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { applicationsApi, clientsApi } from "../lib/api";
import { Button, Card, StatusBadge, Toast, Loading } from "../components/ui";
import { colors, font, spacing, radius } from "../lib/theme";

const FILTERS = ["all", "under_review", "active", "kyc_rejected", "rejected"];

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

export function ApplicationsScreen() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);

  const { data: apps = [], isLoading, refetch } = useQuery({
    queryKey: ["applications", filter],
    queryFn: () => applicationsApi.list(filter === "all" ? undefined : filter),
  });
  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = async () => { setRefreshing(true); await refetch(); setRefreshing(false); };

  const decide = useMutation({
    mutationFn: ({ id, approve, reason }: { id: string; approve: boolean; reason?: string }) =>
      applicationsApi.decide(id, approve, reason),
    onSuccess: (_, v) => {
      setToast({ msg: v.approve ? "Application approved." : "Application rejected.", variant: "success" });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (e) => setToast({ msg: (e as Error).message, variant: "error" }),
  });

  const provision = useMutation({
    mutationFn: clientsApi.processOutbox,
    onSuccess: (r) => {
      setToast({ msg: `Provisioned ${r.processed} client(s).`, variant: "success" });
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e) => setToast({ msg: (e as Error).message, variant: "error" }),
  });

  const handleReject = (id: string) => {
    Alert.prompt?.(
      "Reject Application",
      "Enter reason for rejection:",
      (reason) => {
        if (reason) decide.mutate({ id, approve: false, reason });
      }
    ) ??
      Alert.alert("Reject", "Reject this application?", [
        { text: "Cancel", style: "cancel" },
        { text: "Reject", style: "destructive", onPress: () => decide.mutate({ id, approve: false, reason: "Rejected" }) },
      ]);
  };

  if (isLoading) return <Loading text="Loading applications..." />;

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Applications</Text>
          <Text style={styles.subtitle}>Compliance review queue</Text>
        </View>
        <Button variant="ghost" loading={provision.isPending} onPress={() => provision.mutate()}>
          Provision
        </Button>
      </View>

      {/* Filter Chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
      >
        {FILTERS.map((f) => (
          <Pressable
            key={f}
            onPress={() => setFilter(f)}
            style={[styles.chip, filter === f && styles.chipActive]}
          >
            <Text style={[styles.chipText, filter === f && styles.chipTextActive]}>
              {f.replace(/_/g, " ")}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* List */}
      <FlatList
        data={apps}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>No applications in this view.</Text>
        }
        renderItem={({ item: a }) => (
          <Card style={styles.appCard}>
            <View style={styles.appTop}>
              <View style={{ flex: 1 }}>
                <Text style={styles.appName}>{a.full_name}</Text>
                <Text style={styles.appDetail}>{a.email}</Text>
                <Text style={styles.appDetail}>
                  PAN: {a.pan} · {inr(a.proposed_investment_inr)}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end", gap: 6 }}>
                <StatusBadge status={a.status} />
                <Text style={styles.appRisk}>{a.risk_category ?? "—"}</Text>
              </View>
            </View>
            {a.status === "under_review" && (
              <View style={styles.actions}>
                <Button
                  variant="primary"
                  onPress={() => decide.mutate({ id: a.id, approve: true })}
                >
                  Approve
                </Button>
                <Button variant="danger" onPress={() => handleReject(a.id)}>
                  Reject
                </Button>
              </View>
            )}
          </Card>
        )}
      />

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
    marginTop: spacing.sm,
  },
  title: { ...font.bold, fontSize: 24, color: colors.text },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2 },
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
  appCard: { marginBottom: spacing.sm },
  appTop: { flexDirection: "row", alignItems: "flex-start" },
  appName: { ...font.semibold, fontSize: 16, color: colors.text },
  appDetail: { ...font.regular, fontSize: 13, color: colors.muted, marginTop: 2 },
  appRisk: { ...font.regular, fontSize: 12, color: colors.textSecondary, textTransform: "capitalize" },
  actions: { flexDirection: "row", gap: 10, marginTop: spacing.md },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
});
