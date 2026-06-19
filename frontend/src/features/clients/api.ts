import { apiClient } from "../../lib/apiClient";
import type { Client } from "./types";

export const clientsApi = {
  list: () => apiClient.get<Client[]>("/clients").then((r) => r.data),
  get: (id: string) => apiClient.get<Client>(`/clients/${id}`).then((r) => r.data),
  processOutbox: () =>
    apiClient.post<{ processed: number }>("/clients/process-outbox").then((r) => r.data),
};
