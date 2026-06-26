import { apiClient } from "../../lib/apiClient";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface SessionInfo {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  created_at: string;
  is_current: boolean;
}

export const authApi = {
  register: (data: { email: string; password: string; full_name: string; role?: string; phone?: string; access_code?: string }) =>
    apiClient.post<TokenResponse>("/auth/register", data).then((r) => r.data),

  sendPhoneOtp: (phone?: string) =>
    apiClient.post<{ message: string }>("/auth/send-phone-otp", { phone }).then((r) => r.data),

  verifyPhone: (code: string) =>
    apiClient.post<{ message: string }>("/auth/verify-phone", { code }).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    apiClient.post<TokenResponse>("/auth/login", data).then((r) => r.data),

  refresh: (refresh_token: string) =>
    apiClient.post<TokenResponse>("/auth/refresh", { refresh_token }).then((r) => r.data),

  logout: () =>
    apiClient.post("/auth/logout").then((r) => r.data),

  me: () =>
    apiClient.get<UserProfile>("/auth/me").then((r) => r.data),

  forgotPassword: (email: string) =>
    apiClient.post<{ message: string }>("/auth/forgot-password", { email }).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    apiClient.post<{ message: string }>("/auth/reset-password", { token, new_password }).then((r) => r.data),

  verifyEmail: (token: string) =>
    apiClient.post<{ message: string }>("/auth/verify-email", { token }).then((r) => r.data),

  sessions: () =>
    apiClient.get<SessionInfo[]>("/auth/sessions").then((r) => r.data),

  revokeSession: (sessionId: string) =>
    apiClient.delete(`/auth/sessions/${sessionId}`).then((r) => r.data),

  // Legacy dev token
  devToken: (subject: string, role: string) =>
    apiClient.post<{ access_token: string; token_type: string }>("/auth/dev-token", { subject, role }).then((r) => r.data),
};
