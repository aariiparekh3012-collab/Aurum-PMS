import React, { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { Card, Button } from "../components/ui";
import { auth } from "../lib/auth";
import { colors, font, spacing, radius, shadow } from "../lib/theme";

function InfoRow({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon} size={20} color={colors.gold} style={{ width: 28 }} />
      <View style={{ flex: 1 }}>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={styles.infoValue}>{value}</Text>
      </View>
    </View>
  );
}

export function ProfileScreen({ onLogout }: { onLogout: () => void }) {
  const user = auth.getUser();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          setLoggingOut(true);
          await auth.clear();
          onLogout();
        },
      },
    ]);
  };

  const roleDisplay: Record<string, string> = {
    compliance: "Compliance Officer",
    rm: "Relationship Manager",
    investor: "Investor",
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* Profile Header */}
      <View style={styles.headerWrap}>
        <LinearGradient
          colors={["#1a2235", colors.bg]}
          style={styles.headerBg}
        />
        <View style={[styles.avatar, shadow.gold]}>
          <Text style={styles.avatarText}>
            {user?.subject?.[0]?.toUpperCase() ?? "U"}
          </Text>
        </View>
        <Text style={styles.name}>{user?.subject ?? "User"}</Text>
        <View style={styles.roleBadge}>
          <Text style={styles.roleText}>
            {roleDisplay[user?.role ?? ""] ?? user?.role}
          </Text>
        </View>
      </View>

      {/* Account Info */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>Account</Text>
        <InfoRow icon="person-outline" label="Username" value={user?.subject ?? "—"} />
        <InfoRow icon="shield-checkmark-outline" label="Role" value={roleDisplay[user?.role ?? ""] ?? "—"} />
        <InfoRow icon="server-outline" label="Environment" value="Development" />
      </Card>

      {/* App Info */}
      <Card style={{ marginBottom: spacing.md }}>
        <Text style={styles.sectionTitle}>About</Text>
        <InfoRow icon="diamond-outline" label="App" value="Aurum PMS" />
        <InfoRow icon="code-outline" label="Version" value="1.0.0" />
        <InfoRow icon="ribbon-outline" label="Regulation" value="SEBI PMS 2020" />
      </Card>

      {/* Sign Out */}
      <View style={{ marginTop: spacing.sm }}>
        <Button variant="danger" block loading={loggingOut} onPress={handleLogout}>
          Sign Out
        </Button>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  headerWrap: { alignItems: "center", paddingVertical: spacing.xl, marginBottom: spacing.md },
  headerBg: { position: "absolute", top: 0, left: -spacing.md, right: -spacing.md, height: 160, borderRadius: radius.lg },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  avatarText: { ...font.bold, fontSize: 32, color: colors.bg },
  name: { ...font.bold, fontSize: 24, color: colors.text },
  roleBadge: {
    marginTop: 8,
    paddingVertical: 4,
    paddingHorizontal: 14,
    borderRadius: radius.full,
    backgroundColor: colors.goldDim,
  },
  roleText: { ...font.medium, fontSize: 13, color: colors.gold },
  sectionTitle: { ...font.semibold, fontSize: 16, color: colors.text, marginBottom: spacing.md },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  infoLabel: { ...font.regular, fontSize: 12, color: colors.muted },
  infoValue: { ...font.medium, fontSize: 15, color: colors.text, marginTop: 2 },
});
