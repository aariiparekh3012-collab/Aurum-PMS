import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { Button, Field, SelectField, Toast } from "../../components/ui";
import { onboardingApi } from "../../lib/api";
import { kycSchema, type ApplicationResponse } from "../../lib/types";
import { colors, font, spacing } from "../../lib/theme";

const DEPOSITORIES = [
  { label: "NSDL", value: "NSDL" },
  { label: "CDSL", value: "CDSL" },
];

export function KycStep({
  applicationId,
  onNext,
}: {
  applicationId: string;
  onNext: (a: ApplicationResponse) => void;
}) {
  const [form, setForm] = useState({
    aadhaar_full: "",
    bank_account_number: "",
    bank_ifsc: "",
    bank_holder_name: "",
    demat_bo_id: "",
    demat_depository: "NSDL",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: any) => onboardingApi.submitKyc(applicationId, body),
  });

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  const submit = () => {
    const parsed = kycSchema.safeParse(form);
    if (!parsed.success) {
      const fe: Record<string, string> = {};
      for (const i of parsed.error.issues) fe[i.path[0] as string] = i.message;
      setErrors(fe);
      return;
    }
    setErrors({});
    setApiError(null);
    mutation.mutate(parsed.data, {
      onSuccess: (app) =>
        app.status === "kyc_rejected"
          ? setApiError("KYC failed verification. Please review your details.")
          : onNext(app),
      onError: (e) => setApiError((e as Error).message),
    });
  };

  return (
    <View>
      <Text style={styles.heading}>KYC & Bank Verification</Text>
      <Text style={styles.sub}>Verified via KRA/CKYC & penny-drop (sandbox).</Text>
      <Field label="Aadhaar number" value={form.aadhaar_full} error={errors.aadhaar_full}
        onChangeText={(v) => set("aadhaar_full", v)} placeholder="234567890123" keyboardType="numeric" />
      <Field label="Bank account number" value={form.bank_account_number} error={errors.bank_account_number}
        onChangeText={(v) => set("bank_account_number", v)} placeholder="12345678901" keyboardType="numeric" />
      <Field label="IFSC" value={form.bank_ifsc} error={errors.bank_ifsc}
        onChangeText={(v) => set("bank_ifsc", v.toUpperCase())} placeholder="HDFC0001234" autoCapitalize="characters" />
      <Field label="Account holder name" value={form.bank_holder_name} error={errors.bank_holder_name}
        onChangeText={(v) => set("bank_holder_name", v)} placeholder="Asha Rao" />
      <Field label="Demat BO ID" value={form.demat_bo_id} error={errors.demat_bo_id}
        onChangeText={(v) => set("demat_bo_id", v)} placeholder="1234567812345678" keyboardType="numeric" />
      <SelectField label="Depository" options={DEPOSITORIES}
        value={form.demat_depository} onValueChange={(v) => set("demat_depository", v)} />
      <Button variant="primary" block loading={mutation.isPending} onPress={submit}>
        Verify & Continue
      </Button>
      {apiError && <Toast message={apiError} onDismiss={() => setApiError(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  heading: { ...font.semibold, fontSize: 18, color: colors.text, marginBottom: 4 },
  sub: { ...font.regular, fontSize: 13, color: colors.muted, marginBottom: spacing.md },
});
