import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { Card, Stepper, Button } from "../../components/ui";
import { PersonalStep } from "./PersonalStep";
import { KycStep } from "./KycStep";
import { RiskStep } from "./RiskStep";
import { AgreementStep } from "./AgreementStep";
import type { ApplicationResponse } from "../../lib/types";
import { colors, font, spacing } from "../../lib/theme";

const STEPS = ["Personal", "KYC & Bank", "Risk Profile", "Agreement"];

export function OnboardingScreen() {
  const nav = useNavigation<any>();
  const [step, setStep] = useState(0);
  const [app, setApp] = useState<ApplicationResponse | null>(null);
  const [done, setDone] = useState(false);

  const advance = (a: ApplicationResponse) => {
    setApp(a);
    setStep((s) => s + 1);
  };

  const reset = () => {
    setStep(0);
    setApp(null);
    setDone(false);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>Client Onboarding</Text>
        <Text style={styles.subtitle}>
          Open a discretionary PMS account · minimum ₹50,00,000
        </Text>

        {!done && <Stepper steps={STEPS} current={step} />}

        <Card>
          {done && app ? (
            <View style={styles.successWrap}>
              <View style={styles.successCircle}>
                <Ionicons name="checkmark" size={36} color={colors.bg} />
              </View>
              <Text style={styles.successTitle}>Submitted for review</Text>
              <Text style={styles.successSub}>
                Application {app.id.slice(0, 8)} is now{" "}
                <Text style={{ color: colors.gold }}>
                  {app.status.replace(/_/g, " ")}
                </Text>
                . Compliance will activate the account shortly.
              </Text>
              <View style={styles.successActions}>
                <Button variant="primary" onPress={() => nav.navigate("ClientsTab")}>
                  View Clients
                </Button>
                <Button variant="ghost" onPress={reset}>
                  New Application
                </Button>
              </View>
            </View>
          ) : (
            <>
              {step === 0 && <PersonalStep onNext={advance} />}
              {step === 1 && app && <KycStep applicationId={app.id} onNext={advance} />}
              {step === 2 && app && <RiskStep applicationId={app.id} onNext={advance} />}
              {step === 3 && app && (
                <AgreementStep
                  applicationId={app.id}
                  onDone={(a) => {
                    setApp(a);
                    setDone(true);
                  }}
                />
              )}
            </>
          )}
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.md, paddingBottom: 40 },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 4, marginBottom: spacing.lg },
  successWrap: { alignItems: "center", padding: spacing.md },
  successCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.success,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  successTitle: { ...font.bold, fontSize: 20, color: colors.text, marginBottom: 8 },
  successSub: { ...font.regular, fontSize: 14, color: colors.textSecondary, textAlign: "center", lineHeight: 22 },
  successActions: { flexDirection: "row", gap: 12, marginTop: spacing.lg },
});
