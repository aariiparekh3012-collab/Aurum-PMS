import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { Button, Field, SelectField, Toast } from "../../components/ui";
import { onboardingApi } from "../../lib/api";
import { personalDetailsSchema, type ApplicationResponse } from "../../lib/types";
import { colors, font, spacing } from "../../lib/theme";

const TYPES = [
  { label: "Individual", value: "individual" },
  { label: "HUF", value: "huf" },
  { label: "NRI", value: "nri" },
  { label: "Corporate", value: "corporate" },
];

export function PersonalStep({ onNext }: { onNext: (a: ApplicationResponse) => void }) {
  const [form, setForm] = useState({
    investor_type: "individual",
    full_name: "",
    email: "",
    mobile: "",
    pan: "",
    proposed_investment_inr: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: any) => onboardingApi.createApplication(body),
  });

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  const submit = () => {
    const parsed = personalDetailsSchema.safeParse(form);
    if (!parsed.success) {
      const fe: Record<string, string> = {};
      for (const i of parsed.error.issues) fe[i.path[0] as string] = i.message;
      setErrors(fe);
      return;
    }
    setErrors({});
    setApiError(null);
    mutation.mutate(parsed.data, {
      onSuccess: onNext,
      onError: (e) => setApiError((e as Error).message),
    });
  };

  return (
    <View>
      <Text style={styles.heading}>Personal details</Text>
      <SelectField
        label="Investor type"
        options={TYPES}
        value={form.investor_type}
        onValueChange={(v) => set("investor_type", v)}
      />
      <Field label="Full name" value={form.full_name} error={errors.full_name}
        onChangeText={(v) => set("full_name", v)} placeholder="Asha Rao" />
      <Field label="Email" value={form.email} error={errors.email}
        onChangeText={(v) => set("email", v)} placeholder="asha@example.com"
        keyboardType="email-address" autoCapitalize="none" />
      <Field label="Mobile" value={form.mobile} error={errors.mobile}
        onChangeText={(v) => set("mobile", v)} placeholder="9876543210"
        keyboardType="phone-pad" />
      <Field label="PAN" value={form.pan} error={errors.pan}
        onChangeText={(v) => set("pan", v.toUpperCase())} placeholder="ABCDE1234F"
        autoCapitalize="characters" />
      <Field label="Proposed investment (₹)" value={form.proposed_investment_inr}
        error={errors.proposed_investment_inr}
        onChangeText={(v) => set("proposed_investment_inr", v)} placeholder="5000000"
        keyboardType="numeric" />
      <Button variant="primary" block loading={mutation.isPending} onPress={submit}>
        Continue
      </Button>
      {apiError && <Toast message={apiError} onDismiss={() => setApiError(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  heading: { ...font.semibold, fontSize: 18, color: colors.text, marginBottom: spacing.md },
});
