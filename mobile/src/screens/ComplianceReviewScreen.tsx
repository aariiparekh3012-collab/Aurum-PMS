import React, { useState } from "react";
import {
  Alert,
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
import { complianceApi } from "../lib/api";
import { Card, Button, StatusBadge, KPI, Toast, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { ReviewApplication } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export function ComplianceReviewScreen() {
  const qc = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["compliance-review"],
    queryFn: () => complianceApi.listForReview(),
  });

  const approve = useMutation({
    mutationFn: (id: string) => complianceApi.approveApplication(id),
    onSuccess: () => {
      setToast({ msg: "Application approved.", variant: "success" });
      qc.invalidateQueries({ queryKey: ["compliance-review"] });
      setExpandedId(null);
    },
    onError: (e: Error) => setToast({ msg: e.message, variant: "error" }),
  });

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => complianceApi.rejectApplication(id, reason),
    onSuccess: () => {
      setToast({ msg: "Application rejected.", variant: "success" });
      qc.invalidateQueries({ queryKey: ["compliance-review"] });
      setExpandedId(null);
      setRejectReason("");
    },
    onError: (e: Error) => setToast({ msg: e.message, variant: "error" }),
  });

  const apps = data?.applications || [];
  const total = data?.total || 0;

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const handleReject = (id: string) => {
    if (!rejectReason.trim()) {
      Alert.alert("Reason required", "Please enter a reason for rejection.");
      return;
    }
    reject.mutate({ id, reason: rejectReason });
  };

  return (
    <View style={styles.container}>
      <FadeIn>
        <Text style={styles.title}>Compliance Review</Text>
        <Text style={styles.subtitle}>Applications pending compliance approval</Text>
      </FadeIn>

      <View style={styles.kpiRow}>
        <KPI value={total} label="Pending" />
      </View>

      <FlatList
        data={apps}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
        ListEmptyComponent={
          isLoading
            ? <Loading text="Loading review queue..." />
            : <Text style={styles.empty}>No applications pending review.</Text>
        }
        renderItem={({ item: a }) => {
          const isExpanded = expandedId === a.id;
          return (
            <Pressable onPress={() => setExpandedId(isExpanded ? null : a.id)}>
              <Card style={styles.appCard}>
                <View style={styles.appHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.appName}>{a.full_name}</Text>
                    <Text style={styles.appMeta}>
                      {a.investor_type} · PAN: {a.pan}
                    </Text>
                  </View>
                  <View style={{ alignItems: "flex-end", gap: 4 }}>
                    <Text style={styles.appAmount}>{inr(a.proposed_investment_inr)}</Text>
                    <StatusBadge status={a.status} />
                  </View>
                </View>

                {isExpanded && (
                  <View style={styles.detailSection}>
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Email</Text>
                      <Text style={styles.detailValue}>{a.email}</Text>
                    </View>
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Mobile</Text>
                      <Text style={styles.detailValue}>{a.mobile}</Text>
                    </View>
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Risk Category</Text>
                      <Text style={styles.detailValue}>{a.risk_category || "Not assessed"}</Text>
                    </View>
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Applied</Text>
                      <Text style={styles.detailValue}>{new Date(a.created_at).toLocaleDateString("en-IN")}</Text>
                    </View>

                    {/* Reject reason input */}
                    <TextInput
                      style={styles.reasonInput}
                      placeholder="Rejection reason (required to reject)..."
                      placeholderTextColor={colors.muted}
                      value={rejectReason}
                      onChangeText={setRejectReason}
                      multiline
                      selectionColor={colors.gold}
                    />

                    <View style={styles.actions}>
                      <Button
                        variant="primary"
                        onPress={() => {
                          Alert.alert("Approve?", `Approve ${a.full_name}'s application?`, [
                            { text: "Cancel", style: "cancel" },
                            { text: "Approve", onPress: () => approve.mutate(a.id) },
                          ]);
                        }}
                      >
                        Approve
                      </Button>
                      <Button variant="danger" onPress={() => handleReject(a.id)}>
                        Reject
                      </Button>
                    </View>
                  </View>
                )}

                <View style={styles.expandHint}>
                  <Ionicons
                    name={isExpanded ? "chevron-up" : "chevron-down"}
                    size={16}
                    color={colors.muted}
                  />
                </View>
              </Card>
            </Pressable>
          );
        }}
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
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
  appCard: { marginBottom: spacing.sm },
  appHeader: { flexDirection: "row", alignItems: "flex-start" },
  appName: { ...font.semibold, fontSize: 16, color: colors.text },
  appMeta: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  appAmount: { ...font.semibold, fontSize: 15, color: colors.gold },
  detailSection: { marginTop: spacing.md, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: spacing.md },
  detailRow: {
    flexDirection: "row", justifyContent: "space-between",
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  detailLabel: { ...font.regular, fontSize: 13, color: colors.muted },
  detailValue: { ...font.medium, fontSize: 13, color: colors.text },
  reasonInput: {
    backgroundColor: colors.bgInput, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.line, color: colors.text,
    paddingHorizontal: spacing.md, paddingVertical: 12,
    fontSize: 14, marginTop: spacing.md, minHeight: 60, textAlignVertical: "top",
  },
  actions: { flexDirection: "row", gap: 10, marginTop: spacing.md },
  expandHint: { alignItems: "center", marginTop: 8 },
});
