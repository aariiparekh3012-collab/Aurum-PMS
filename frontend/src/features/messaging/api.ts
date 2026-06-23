import { apiClient } from "../../lib/apiClient";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Contact {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

export interface Message {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  participants: Contact[];
  last_message: Message | null;
  unread_count: number;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  participants: Contact[];
  messages: Message[];
}

// ── API ──────────────────────────────────────────────────────────────────────

export const messagingApi = {
  contacts: () =>
    apiClient.get<Contact[]>("/messages/contacts").then((r) => r.data),

  conversations: () =>
    apiClient.get<Conversation[]>("/messages/conversations").then((r) => r.data),

  conversation: (id: string) =>
    apiClient.get<ConversationDetail>(`/messages/conversations/${id}`).then((r) => r.data),

  startConversation: (recipientId: string, body: string) =>
    apiClient
      .post<ConversationDetail>("/messages/conversations", {
        recipient_id: recipientId,
        body,
      })
      .then((r) => r.data),

  sendMessage: (conversationId: string, body: string) =>
    apiClient
      .post<Message>(`/messages/conversations/${conversationId}/messages`, { body })
      .then((r) => r.data),

  unreadCount: () =>
    apiClient.get<{ count: number }>("/messages/unread-count").then((r) => r.data),
};
