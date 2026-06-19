import { apiClient } from "../../lib/apiClient";

export interface Activity {
  id: string;
  actor_role: string;
  actor_subject: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: string | null;
  is_read: boolean;
  created_at: string;
}

export interface FeedResponse {
  items: Activity[];
  total: number;
  unread: number;
}

export interface UnreadCount {
  count: number;
}

export const notificationsApi = {
  feed: (entityType?: string, limit = 30, offset = 0) =>
    apiClient
      .get<FeedResponse>("/notifications/feed", {
        params: { entity_type: entityType || undefined, limit, offset },
      })
      .then((r) => r.data),

  unreadCount: () =>
    apiClient.get<UnreadCount>("/notifications/unread-count").then((r) => r.data),

  log: (data: { action: string; entity_type: string; entity_id?: string; detail?: string }) =>
    apiClient.post<Activity>("/notifications/log", data).then((r) => r.data),

  markAllRead: () =>
    apiClient.post("/notifications/mark-read").then((r) => r.data),

  markOneRead: (id: string) =>
    apiClient.post("/notifications/mark-read/" + id).then((r) => r.data),
};
