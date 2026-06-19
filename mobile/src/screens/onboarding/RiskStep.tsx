import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { Button, SelectField, Toast } from "../../components/ui";
import { onboardingApi } from "../../lib/api";
import type { ApplicationResponse } from "../../lib/types";
import { colors, font, spacing } from "../../lib/theme";

const QUESTIONS = [
  "What is your investment horizon?",
  "How would you react to a 20% portfolio drop?",
  "What share of your wealth is being invested here?",
  "What is your primary objective?",
  "What is your prior experience with equities?",
];

const OPTIONS = [
  { label: "Very low risk", value: "1" },
  { label: "Low", value: "2" },
  { label: "Medium", value: "3" },
  { label: "High", value: "4" },
  { label: "Very high risk", value: "5" },
];

export function RiskStep({
  applicationId,
  onNext,
}: {
  applicationId: string;
  onNext: (a: ApplicationResponse) => void;
}) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: any[]) =>
      onboardingApi.completeRiskProfile(applicationId, payload),
  });

  const submit = () => {
    if (Object.keys(answers).length < QUESTIONS.length) {
      setApiError("Please answer all questions.");
      return;
    }
    setApiError(null);
    const payload = QUESTIONS.map((_, i) => ({
      question_id: `q${i}`,
      weight: Number(answers[i]),
    }));
    mutation.mutate(payload, {
      onSuccess: onNext,
      onError: (e) => setApiError((e as Error).message),
    });
  };

  return (
    <View>
      <Text style={styles.heading}>Risk Profiling</Text>
      {QUESTIONS.map((q, i) => (
        <SelectField
          key={i}
          label={`${i + 1}. ${q}`}
          options={OPTIONS}
          value={answers[i] ?? ""}
          onValueChange={(v) => setAnswers({ ...answers, [i]: v })}
        />
      ))}
      <Button variant="primary" block loading={mutation.isPending} onPress={submit}>
        Submit Risk Profile
      </Button>
      {apiError && <Toast message={apiError} onDismiss={() => setApiError(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  heading: { ...font.semibold, fontSize: 18, color: colors.text, marginBottom: spacing.md },
});
