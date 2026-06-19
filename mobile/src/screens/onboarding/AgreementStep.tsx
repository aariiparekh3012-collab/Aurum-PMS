import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { Button, Card, Toast } from "../../components/ui";
import { onboardingApi } from "../../lib/api";
import type { ApplicationResponse } from "../../lib/types";
import { colors, font, spacing, radius } from "../../lib/theme";

export function AgreementStep({
  applicationId,
  onDone,
}: {
  applicationId: string;
  onDone: (a: ApplicationResponse) => void;
}) {
  const [accepted, setAccepted] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => onboardingApi.confirmEsign(applicationId, "TXN-SANDBOX"),
  });

  const sign = () => {
    setApiError(null);
    mutation.mutate(undefined, {
      onSuccess: onDone,
      onError: (e) => setApiError((e as Error).message),
    });
  };

  return (
    <View>
      <Text style={styles.heading}>PMS Agreement</Text>

      <View style={styles.agreementBox}>
        <Text style={styles.agreementText}>
          This Portfolio Management Services Agreement is entered into between the
          Portfolio Manager and the Client, governing discretionary management of the
          Client's funds and securities under the SEBI (Portfolio Managers) Regulations,
          2020 — including the minimum investment of ₹50,00,000, fee disclosures, the
          Disclosure Document, and the Client's risk profile and investment approach.
        </Text>
      </View>

      <Pressable onPress={() => setAccepted(!accepted)} style={styles.checkRow}>
        <View style={[styles.checkbox, accepted && styles.checkboxChecked]}>
          {accepted && <Ionicons name="checkmark" size={16} color={colors.bg} />}
        </View>
        <Text style={styles.checkLabel}>
          I have read and agree to the PMS Agreement and Disclosure Document.
        </Text>
      </Pressable>

      <Button
        variant="primary"
        block
        disabled={!accepted}
        loading={mutation.isPending}
        onPress={sign}
      >
        eSign with Aadhaar
      </Button>
      {apiError && <Toast message={apiError} onDismiss={() => setApiError(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  heading: { ...font.semibold, fontSize: 18, color: colors.text, marginBottom: spacing.md },
  agreementBox: {
    backgroundColor: colors.bgInput,
    borderRadius: radius.md,
    padding: spacing.md,
    maxHeight: 180,
    marginBottom: spacing.md,
  },
  agreementText: { ...font.regular, fontSize: 14, color: colors.muted, lineHeight: 22 },
  checkRow: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: spacing.lg },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: { backgroundColor: colors.gold, borderColor: colors.gold },
  checkLabel: { ...font.regular, fontSize: 14, color: colors.textSecondary, flex: 1 },
});
