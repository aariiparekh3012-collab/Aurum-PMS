import { apiClient } from "../../lib/apiClient";

export interface ReviewApplication {
  id: string;
  full_name: string;
  email: string;
  mobile: string;
  investor_type: string;
  proposed_investment_inr: number;
  status: string;
  risk_category: string | null;
  pan: string;
  created_at: string;
  updated_at: string;
}

interface ReviewListResponse {
  applications: ReviewApplication[];
  total: number;
  limit: number;
  offset: number;
}

export const complianceApi = {
  listForReview: (limit: number = 50, offset: number = 0): Promise<ReviewListResponse> =>
    apiClient
      .get("/onboarding/applications/review/pending", { params: { limit, offset } })
      .then((r) => r.data),

  getApplicationDetail: (applicationId: string): Promise<ReviewApplication> =>
    apiClient.get(`/onboarding/applications/${applicationId}`).then((r) => r.data),

  approveApplication: (applicationId: string, reason?: string) =>
    apiClient
      .post(`/onboarding/applications/${applicationId}/decision`, { approve: true, reason })
      .then((r) => r.data),

  rejectApplication: (applicationId: string, reason: string) =>
    apiClient
      .post(`/onboarding/applications/${applicationId}/decision`, { approve: false, reason })
      .then((r) => r.data),
};
