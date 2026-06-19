import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useRoute } from "@react-navigation/native";
import { Card, StatusBadge, Loading } from "../components/ui";
import { clientsApi } from "../lib/api";
import { colors, font, spacing } from "../lib/theme";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

export function ClientDetailScreen() {
  const { params } = useRoute<any>();
  const { data: c, isLoading, error } = useQuery({
    queryKey: ["client", params.id],
    queryFn: () => clientsApi.get(params.id),
  });

  if (isLoading) return <Loading text="Loading..." />;
  if (error || !c) return <Text style={styles.empty}>Client not found.</Text>;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{c.full_name[0]}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{c.full_name}</Text>
          <Text style={styles.code}>{c.client_code}</Text>
        </View>
        <StatusBadge status={c.status} />
      </View>

      {/* Profile */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Profile</Text>
        <Row label="PAN" value={c.pan} />
        <Row label="Investor type" value={c.investor_type} />
        <Row label="Email" value={c.email} />
        <Row label="Mobile" value={c.mobile} />
        <Row label="Risk profile" value={c.risk_category ?? "—"} />
      </Card>

      {/* Bank & Demat */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Bank & Demat</Text>
        {c.bank_accounts.length === 0 ? (
          <Text style={styles.faint}>No bank accounts.</Text>
        ) : (
          c.bank_accounts.map((b, i) => (
            <Row
              key={i}
              label={`${b.ifsc}${b.is_primary ? " · primary" : ""}`}
              value={b.masked_account}
            />
          ))
        )}
        {c.demat_bo_ids.map((d, i) => (
          <Row key={`d${i}`} label="Demat BO ID" value={d} />
        ))}
      </Card>

      {/* Nominees */}
      <Card>
        <Text style={styles.sectionTitle}>Nominees</Text>
        {c.nominees.length === 0 ? (
          <Text style={styles.faint}>No nominees on record.</Text>
        ) : (
          c.nominees.map((n, i) => (
            <View key={i} style={styles.nomineeRow}>
              <Text style={styles.nomineeRank}>#{n.rank}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.nomineeName}>{n.name}</Text>
                <Text style={styles.nomineeRel}>{n.relationship ?? "—"}</Text>
              </View>
              <Text style={styles.nomineeShare}>{n.share_percent}%</Text>
            </View>
          ))
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    marginBottom: spacing.lg,
    marginTop: spacing.sm,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { ...font.bold, fontSize: 22, color: colors.gold },
  name: { ...font.bold, fontSize: 22, color: colors.text },
  code: { ...font.regular, fontSize: 13, color: colors.muted, marginTop: 2 },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.md },
  detailRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  detailLabel: { ...font.regular, fontSize: 14, color: colors.textSecondary },
  detailValue: { ...font.medium, fontSize: 14, color: colors.text, textTransform: "capitalize" },
  faint: { color: colors.muted, ...font.regular, fontSize: 14 },
  nomineeRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    gap: 12,
  },
  nomineeRank: { ...font.bold, fontSize: 16, color: colors.gold, width: 30 },
  nomineeName: { ...font.medium, fontSize: 14, color: colors.text },
  nomineeRel: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  nomineeShare: { ...font.semibold, fontSize: 14, color: colors.gold },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", padding: 40 },
});
