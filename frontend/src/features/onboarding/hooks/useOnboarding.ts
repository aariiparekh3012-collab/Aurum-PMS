import { useMutation } from "@tanstack/react-query";
import { onboardingApi } from "../api/onboardingApi";
import type { KycDetails, PersonalDetails, RiskAnswer } from "../types";

/** React Query mutations encapsulating each onboarding step. */
export function useCreateApplication() {
  return useMutation({
    mutationFn: (body: PersonalDetails) => onboardingApi.createApplication(body),
  });
}

export function useSubmitKyc(applicationId: string) {
  return useMutation({
    mutationFn: (body: KycDetails) => onboardingApi.submitKyc(applicationId, body),
  });
}

export function useRiskProfile(applicationId: string) {
  return useMutation({
    mutationFn: (answers: RiskAnswer[]) =>
      onboardingApi.completeRiskProfile(applicationId, answers),
  });
}

export function useConfirmEsign(applicationId: string) {
  return useMutation({
    mutationFn: (transactionId: string) =>
      onboardingApi.confirmEsign(applicationId, transactionId),
  });
}
