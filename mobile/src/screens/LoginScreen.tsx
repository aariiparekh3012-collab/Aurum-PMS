import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Button, Card, Field, Toast } from "../components/ui";
import { apiClient } from "../lib/apiClient";
import { auth } from "../lib/auth";
import { colors, font, radius, spacing, shadow } from "../lib/theme";

export function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signIn = async () => {
    if (!email.trim() || !password) {
      setError("Email and password are required");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Real backend auth: credentials are verified server-side.
      const { data } = await apiClient.post("/auth/login", {
        email: email.trim(),
        password,
      });
      await auth.setSession(data.access_token, { subject: email.trim(), role: "" });
      // Fetch profile to get the server-assigned role.
      const me = await apiClient.get("/auth/me");
      await auth.setSession(data.access_token, {
        subject: me.data.full_name || me.data.email,
        role: me.data.role,
      });
      onLogin();
    } catch (e) {
      await auth.clear();
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={["#0a0e17", "#111827", "#0a0e17"]} style={styles.gradient}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {/* Brand */}
          <View style={styles.brand}>
            <View style={[styles.brandMark, shadow.gold]}>
              <Text style={styles.brandLetter}>P</Text>
            </View>
            <Text style={styles.title}>Aurum PMS</Text>
            <Text style={styles.subtitle}>
              Discretionary Portfolio Management
            </Text>
            <LinearGradient
              colors={["transparent", colors.gold, "transparent"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.divider}
            />
          </View>

          {/* Form */}
          <Card glass>
            <Text style={styles.formTitle}>Sign in</Text>
            <Field
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <Field
              label="Password"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
            />
            <View style={{ marginTop: 8 }}>
              <Button variant="primary" block loading={loading} onPress={signIn}>
                Enter Dashboard
              </Button>
            </View>
            <Text style={styles.footerNote}>
              SEBI-registered · Secure sign-in
            </Text>
          </Card>
        </ScrollView>
      </KeyboardAvoidingView>
      {error && <Toast message={error} onDismiss={() => setError(null)} />}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: { flex: 1 },
  scroll: {
    flexGrow: 1,
    justifyContent: "center",
    padding: spacing.lg,
  },
  brand: { alignItems: "center", marginBottom: 28 },
  brandMark: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  brandLetter: {
    ...font.bold,
    fontSize: 28,
    color: "#0a0e17",
  },
  title: {
    ...font.bold,
    fontSize: 32,
    color: colors.text,
    letterSpacing: -0.5,
  },
  subtitle: {
    ...font.regular,
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  divider: {
    width: 48,
    height: 2,
    borderRadius: 1,
    marginTop: spacing.md,
  },
  formTitle: {
    ...font.semibold,
    fontSize: 20,
    color: colors.text,
    marginBottom: 20,
  },
  footerNote: {
    ...font.regular,
    fontSize: 11,
    color: colors.muted,
    textAlign: "center",
    marginTop: 20,
  },
});
