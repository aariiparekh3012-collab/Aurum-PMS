import React, { useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { auth } from "../lib/auth";
import { Card, Button, Toast } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import { colors, font, spacing, radius } from "../lib/theme";

type Tab = "profile" | "notifications" | "appearance";

interface Prefs {
  email_enabled: boolean;
  order_alerts: boolean;
  trade_alerts: boolean;
  application_alerts: boolean;
}

const PREF_OPTIONS: { key: keyof Prefs; label: string; desc: string }[] = [
  { key: "email_enabled", label: "Email notifications", desc: "Receive email alerts for important events" },
  { key: "order_alerts", label: "Order alerts", desc: "New orders, approvals, and rejections" },
  { key: "trade_alerts", label: "Trade alerts", desc: "Trade executions and confirmations" },
  { key: "application_alerts", label: "Application alerts", desc: "Onboarding status changes" },
];

const ROLE_PERMISSIONS: Record<string, string[]> = {
  compliance: [
    "View all clients & applications",
    "Approve / reject applications",
    "Provision clients from approved apps",
    "Manage securities, strategies, brokers",
    "View & generate reports",
    "Access compliance review queue",
    "Seed reference data",
  ],
  rm: [
    "View all clients & applications",
    "Submit new onboarding applications",
    "Create orders and record trades",
    "Manage portfolio accounts",
    "View & generate reports",
  ],
  investor: [
    "View own portfolio holdings",
    "View own cash ledger",
    "Track onboarding status",
    "View activity feed",
  ],
};

export function SettingsScreen() {
  const user = auth.getUser();
  const [tab, setTab] = useState<Tab>("profile");
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const [prefs, setPrefs] = useState<Prefs>({
    email_enabled: true,
    order_alerts: true,
    trade_alerts: true,
    application_alerts: true,
  });

  const togglePref = (key: keyof Prefs) => setPrefs((p) => ({ ...p, [key]: !p[key] }));

  const permissions = ROLE_PERMISSIONS[user?.role || ""] || [];

  const tabs: { key: Tab; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
    { key: "profile", label: "Profile", icon: "person-outline" },
    { key: "notifications", label: "Alerts", icon: "notifications-outline" },
    { key: "appearance", label: "Display", icon: "color-palette-outline" },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      <FadeIn>
        <Text style={styles.title}>Settings</Text>
        <Text style={styles.subtitle}>Profile, notifications & preferences</Text>
      </FadeIn>

      {/* Tab bar */}
      <View style={styles.tabRow}>
        {tabs.map((t) => (
          <Pressable
            key={t.key}
            onPress={() => setTab(t.key)}
            style={[styles.tabBtn, tab === t.key && styles.tabBtnActive]}
          >
            <Ionicons name={t.icon} size={16} color={tab === t.key ? colors.gold : colors.muted} />
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>

      {/* ── Profile ── */}
      {tab === "profile" && (
        <>
          <Card style={{ marginBottom: spacing.md }}>
            <View style={styles.profileHeader}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{(user?.subject ?? "U")[0].toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1, marginLeft: 16 }}>
                <Text style={styles.profileName}>{user?.subject ?? "Guest"}</Text>
                <Text style={styles.profileRole}>{user?.role ?? "unknown"}</Text>
              </View>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Username</Text>
              <Text style={styles.infoValue}>{user?.subject ?? "—"}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Role</Text>
              <Text style={[styles.infoValue, { textTransform: "capitalize" }]}>{user?.role ?? "—"}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Auth method</Text>
              <Text style={styles.infoValue}>Dev token (JWT)</Text>
            </View>
          </Card>

          <Card>
            <Text style={styles.sectionTitle}>Role Permissions</Text>
            <Text style={styles.permissionsDesc}>
              Access levels are determined by your assigned role.
            </Text>
            {permissions.map((p) => (
              <View key={p} style={styles.permRow}>
                <Ionicons name="checkmark-circle" size={16} color={colors.success} />
                <Text style={styles.permText}>{p}</Text>
              </View>
            ))}
          </Card>
        </>
      )}

      {/* ── Notifications ── */}
      {tab === "notifications" && (
        <Card>
          <Text style={styles.sectionTitle}>Notification Preferences</Text>
          <Text style={styles.permissionsDesc}>
            Control which notifications you receive.
          </Text>
          {PREF_OPTIONS.map(({ key, label, desc }) => (
            <View key={key} style={styles.prefRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.prefLabel}>{label}</Text>
                <Text style={styles.prefDesc}>{desc}</Text>
              </View>
              <Switch
                value={prefs[key]}
                onValueChange={() => togglePref(key)}
                trackColor={{ false: colors.bgInput, true: colors.gold }}
                thumbColor={prefs[key] ? colors.bg : colors.muted}
              />
            </View>
          ))}
          <Button
            variant="primary"
            onPress={() => setToast({ msg: "Preferences saved.", variant: "success" })}
            style={{ marginTop: spacing.md }}
          >
            Save Preferences
          </Button>
        </Card>
      )}

      {/* ── Appearance ── */}
      {tab === "appearance" && (
        <Card>
          <Text style={styles.sectionTitle}>Appearance</Text>
          {[
            { label: "Theme", value: "Premium Dark", desc: "Dark mode with gold accents" },
            { label: "Currency", value: "INR", desc: "Format for monetary values" },
            { label: "Date format", value: "DD/MM/YYYY", desc: "How dates are displayed" },
            { label: "Timezone", value: "IST (UTC+5:30)", desc: "Market hours reference" },
          ].map((item) => (
            <View key={item.label} style={styles.appearRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.appearLabel}>{item.label}</Text>
                <Text style={styles.appearDesc}>{item.desc}</Text>
              </View>
              <Text style={styles.appearValue}>{item.value}</Text>
            </View>
          ))}
          <Text style={styles.futureNote}>
            Additional themes and customization options coming soon.
          </Text>
        </Card>
      )}

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: 8 },
  tabRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  tabBtn: {
    flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    paddingVertical: 12, borderRadius: radius.md, backgroundColor: colors.bgInput,
    borderWidth: 1, borderColor: colors.line,
  },
  tabBtnActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  tabText: { ...font.medium, fontSize: 13, color: colors.muted },
  tabTextActive: { color: colors.gold },
  profileHeader: { flexDirection: "row", alignItems: "center", marginBottom: spacing.md },
  avatar: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: colors.gold, alignItems: "center", justifyContent: "center",
  },
  avatarText: { ...font.bold, fontSize: 22, color: "#1a1305" },
  profileName: { ...font.semibold, fontSize: 18, color: colors.text },
  profileRole: { ...font.regular, fontSize: 13, color: colors.gold, textTransform: "capitalize", marginTop: 2 },
  infoRow: {
    flexDirection: "row", justifyContent: "space-between",
    paddingVertical: 12, borderTopWidth: 1, borderTopColor: colors.line,
  },
  infoLabel: { ...font.regular, fontSize: 13, color: colors.muted },
  infoValue: { ...font.medium, fontSize: 14, color: colors.text },
  permissionsDesc: { ...font.regular, fontSize: 13, color: colors.muted, marginBottom: spacing.md },
  permRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 6 },
  permText: { ...font.regular, fontSize: 14, color: colors.text },
  prefRow: {
    flexDirection: "row", alignItems: "center", paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  prefLabel: { ...font.medium, fontSize: 15, color: colors.text },
  prefDesc: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  appearRow: {
    flexDirection: "row", alignItems: "center", paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  appearLabel: { ...font.medium, fontSize: 15, color: colors.text },
  appearDesc: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  appearValue: { ...font.medium, fontSize: 13, color: colors.gold },
  futureNote: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: spacing.md },
});
