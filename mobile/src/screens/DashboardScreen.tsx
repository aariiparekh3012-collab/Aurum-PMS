import React from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { Card, KPI, StatusBadge, Loading } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import { DonutChart, BarChart, palette, type Slice } from "../components/Charts";
import { dashboardApi, applicationsApi } from "../lib/api";
import { auth } from "../lib/auth";
import { colors, font, spacing, radius, shadow } from "../lib/theme";

export function DashboardScreen() {
  const nav = useNavigation<any>();
  const user = auth.getUser();

  const { data: stats, isLoading, refetch: refetchStats } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
  });
  const { data: recentApps = [], refetch: refetchApps } = useQuery({
    queryKey: ["applications", "all"],
    queryFn: () => applicationsApi.list(),
  });
  const [refreshing, setRefreshing] = React.useState(false);
  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([refetchStats(), refetchApps()]);
    setRefreshing(false);
  };

  if (isLoading || !stats) return <Loading text="Loading dashboard..." />;

  const statusData: Slice[] = stats.applications_by_status.map((s, i) => ({
    label: s.status.replace(/_/g, " "),
    value: s.count,
    color: palette(i),
  }));
  const riskData: Slice[] = stats.clients_by_risk.map((r, i) => ({
    label: r.category,
    value: r.count,
    color: palette(i),
  }));
  const recent = recentApps.slice(0, 5);

  const quickActions = [
    { icon: "add-circle-outline" as const, title: "New Onboarding", sub: "Start application", route: "OnboardingTab" },
    { icon: "documents-outline" as const, title: "Review Queue", sub: `${stats.pending_review} pending`, route: "ApplicationsTab" },
    { icon: "people-outline" as const, title: "Clients", sub: `${stats.total_clients} onboarded`, route: "ClientsTab" },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: 40 }}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
      }
    >
      {/* Header */}
      <FadeIn><View style={styles.header}>
        <Text style={styles.greeting}>
          Welcome back, <Text style={{ color: colors.gold }}>{user?.subject ?? "User"}</Text>
        </Text>
        <Text style={styles.subGreeting}>Aurum PMS — Platform overview</Text>
      </View></FadeIn>

      {/* KPIs */}
      <View style={styles.kpiRow}>
        <KPI value={stats.total_clients} label="Total clients" />
        <KPI value={stats.active_clients} label="Active" />
      </View>
      <View style={styles.kpiRow}>
        <KPI value={stats.total_applications} label="Applications" />
        <KPI
          value={
            <Text style={stats.pending_review > 0 ? { color: colors.warning } : undefined}>
              {stats.pending_review}
            </Text>
          }
          label="Pending review"
        />
      </View>

      {/* Quick Actions */}
      <View style={styles.actionsRow}>
        {quickActions.map((a) => (
          <Card
            key={a.title}
            glass
            style={styles.actionCard}
            onPress={() => nav.navigate(a.route)}
          >
            <Ionicons name={a.icon} size={28} color={colors.gold} />
            <Text style={styles.actionTitle}>{a.title}</Text>
            <Text style={styles.actionSub}>{a.sub}</Text>
          </Card>
        ))}
      </View>

      {/* Charts */}
      {statusData.length > 0 && (
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>Application Status</Text>
          <DonutChart data={statusData} />
        </Card>
      )}
      {riskData.length > 0 && (
        <Card style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>Client Risk Profiles</Text>
          <BarChart data={riskData} />
        </Card>
      )}

      {/* Recent Applications */}
      <Card>
        <Text style={styles.sectionTitle}>Recent Applications</Text>
        {recent.length === 0 ? (
          <Text style={styles.empty}>No applications yet.</Text>
        ) : (
          recent.map((a) => (
            <View key={a.id} style={styles.appRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.appName}>{a.full_name}</Text>
                <Text style={styles.appEmail}>{a.email}</Text>
              </View>
              <View style={{ alignItems: "flex-end", gap: 4 }}>
                <StatusBadge status={a.status} />
                <Text style={styles.appRisk}>{a.risk_category ?? "—"}</Text>
              </View>
            </View>
          ))
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  header: { marginBottom: spacing.lg, marginTop: spacing.sm },
  greeting: { ...font.bold, fontSize: 24, color: colors.text },
  subGreeting: { ...font.regular, fontSize: 14, color: colors.textSecondary, marginTop: 4 },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.sm },
  actionsRow: { flexDirection: "row", gap: spacing.sm, marginVertical: spacing.md },
  actionCard: { flex: 1, alignItems: "center", padding: spacing.md },
  actionTitle: { ...font.semibold, fontSize: 13, color: colors.text, marginTop: 8, textAlign: "center" },
  actionSub: { ...font.regular, fontSize: 11, color: colors.muted, marginTop: 2, textAlign: "center" },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.md },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 20 },
  appRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  appName: { ...font.medium, fontSize: 15, color: colors.text },
  appEmail: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  appRisk: { ...font.regular, fontSize: 12, color: colors.textSecondary, textTransform: "capitalize" },
});
