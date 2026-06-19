export interface PersonalDetails {
  investor_type: string;
  full_name: string;
  email: string;
  mobile: string;
  pan: string;
  proposed_investment_inr: number;
}

export interface KycDetails {
  aadhaar_full: string;
  bank_account_number: string;
  bank_ifsc: string;
  bank_holder_name: string;
  demat_bo_id: string;
  demat_depository: string;
}

export interface RiskAnswer {
  question_id: string;
  weight: number;
}

export interface ApplicationResponse {
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

export type OnboardingStep = "personal" | "kyc" | "risk" | "agreement" | "done";
