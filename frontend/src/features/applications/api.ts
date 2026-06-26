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
  list: (status?: string): Promise<Application[]> =>
    apiClient
      .get<{ applications: Application[] } | Application[]>("/onboarding/applications", { params: status ? { status } : {} })
      .then((r) => (Array.isArray(r.data) ? r.data : (r.data as { applications: Application[] }).applications ?? [])),
  decide: (id: string, approve: boolean, reason?: string) =>
    apiClient
      .post(`/onboarding/applications/${id}/decision`, { approve, reason })
      .then((r) => r.data),
};
