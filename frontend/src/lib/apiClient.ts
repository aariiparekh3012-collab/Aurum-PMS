import axios from "axios";
import { auth } from "./auth";

export const apiClient = axios.create({
  baseURL: "/api/v1",
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
