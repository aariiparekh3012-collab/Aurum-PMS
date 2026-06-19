import axios from "axios";
import Constants from "expo-constants";
import { auth } from "./auth";

// URL priority: app.json extra.apiBaseUrl → Android emulator fallback → iOS fallback
const BASE_URL: string =
  Constants.expoConfig?.extra?.apiBaseUrl ||
  (Constants.platform?.android
    ? "http://10.0.2.2:8000/api/v1"   // Android emulator: 10.0.2.2 = host machine
    : "http://localhost:8000/api/v1"); // iOS simulator

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const token = auth.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      auth.clear();
    }
    const apiError = error.response?.data?.error;
    return Promise.reject(
      new Error(apiError?.message ?? error.message ?? "Request failed")
    );
  }
);
