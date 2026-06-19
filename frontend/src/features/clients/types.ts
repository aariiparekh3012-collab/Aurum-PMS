export interface BankAccount {
  ifsc: string;
  holder_name: string;
  masked_account: string;
  is_primary: boolean;
}

export interface Nominee {
  name: string;
  share_percent: number;
  rank: number;
  relationship: string | null;
}

export interface Client {
  id: string;
  client_code: string;
  status: string;
  investor_type: string;
  full_name: string;
  email: string;
  mobile: string;
  pan: string;
  onboarding_application_id: string;
  risk_category: string | null;
  demat_bo_ids: string[];
  bank_accounts: BankAccount[];
  nominees: Nominee[];
}
