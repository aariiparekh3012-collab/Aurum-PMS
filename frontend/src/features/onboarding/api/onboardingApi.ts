import { apiClient } from "@/lib/apiClient";
import type {
  ApplicationResponse,
  KycDetails,
  PersonalDetails,
  RiskAnswer,
} from "../types";

/** Typed wrappers around the onboarding REST endpoints. */
export const onboardingApi = {
  createApplication: (body: PersonalDetails) =>
    apiClient
      .post<ApplicationResponse>("/onboarding/applications", body)
      .then((r) => r.data),

  submitKyc: (id: string, body: KycDetails) =>
    apiClient
      .post<ApplicationResponse>(`/onboarding/applications/${id}/kyc`, body)
      .then((r) => r.data),

  completeRiskProfile: (id: string, answers: RiskAnswer[]) =>
    apiClient
      .post<ApplicationResponse>(`/onboarding/applications/${id}/risk-profile`, {
        answers,
      })
      .then((r) => r.data),

  confirmEsign: (id: string, transactionId: string) =>
    apiClient
      .post<ApplicationResponse>(`/onboarding/applications/${id}/esign/confirm`, {
        transaction_id: transactionId,
      })
      .then((r) => r.data),
};
