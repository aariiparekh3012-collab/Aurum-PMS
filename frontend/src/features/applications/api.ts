import { apiClient } from "../../lib/apiClient";

export interface Application {
  id: string;
  status: string;
  investor_type: string;
  full_name: string;
  email: string;
  pan: string;
  proposed_investment_inr: number;
  risk_category: string | null;
  kyc_source: string | null;
}

export const applicationsApi = {
  list: (status?: string) =>
    apiClient
      .get<Application[]>("/onboarding/applications", { params: status ? { status } : {} })
      .then((r) => r.data),
  decide: (id: string, approve: boolean, reason?: string) =>
    apiClient
      .post(`/onboarding/applications/${id}/decision`, { approve, reason })
      .then((r) => r.data),
};
