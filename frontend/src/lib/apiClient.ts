import axios from "axios";
import { auth } from "./auth";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? "https://aurum-pms-backend.onrender.com/api/v1" : "/api/v1");

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from auth store on every request
apiClient.interceptors.request.use((config) => {
  const token = auth.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Surface error messages from the API; auto-logout on 401
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "Something went wrong";

    if (status === 401) {
      auth.clear();
    }

    return Promise.reject(new Error(msg));
  },
);
