import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { apiClient } from "../lib/apiClient";
import { colors, font, radius, spacing, shadow } from "../lib/theme";

// ── Types ───────────────────────────────────────────────────────────────────

interface Contact {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

interface Message {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  created_at: string;
}

interface Conversation {
  id: string;
  participants: Contact[];
  last_message: Message | null;
  unread_count: number;
  updated_at: string;
}

interface ConversationDetail {
  id: string;
  participants: Contact[];
  messages: Message[];
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  compliance: "Compliance",
  rm: "RM",
  relationship_manager: "RM",
  investor: "Investor",
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function initial(name: string) {
  return name?.[0]?.toUpperCase() ?? "?";
}

// ── Component ───────────────────────────────────────────────────────────────

type Screen = "list" | "chat" | "new" | "contacts";

export function MessagesScreen() {
  const [screen, setScreen] = useState<Screen>("list");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [activeConv, setActiveConv] = useState<ConversationDetail | null>(null);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [msgText, setMsgText] = useState("");
  const [sending, setSending] = useState(false);
  const [contactSearch, setContactSearch] = useState("");
  const flatListRef = useRef<FlatList>(null);

  // ── Data fetching ─────────────────────────────────────────────────────

  const fetchConversations = useCallback(async () => {
    try {
      const { data } = await apiClient.get("/messages/conversations");
      setConversations(data);
    } catch { /* ignore */ }
  }, []);

  const fetchContacts = useCallback(async () => {
    try {
      const { data } = await apiClient.get("/messages/contacts");
      setContacts(data);
    } catch { /* ignore */ }
  }, []);

  const fetchConversation = useCallback(async (convId: string) => {
    try {
      const { data } = await apiClient.get(`/messages/conversations/${convId}`);
      setActiveConv(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    (async () => {
      await fetchConversations();
      setLoading(false);
    })();
  }, [fetchConversations]);

  // Poll for new messages when in chat view
  useEffect(() => {
    if (screen !== "chat" || !activeConvId) return;
    const interval = setInterval(() => fetchConversation(activeConvId), 5000);
    return () => clearInterval(interval);
  }, [screen, activeConvId, fetchConversation]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchConversations();
    setRefreshing(false);
  };

  // ── Actions ───────────────────────────────────────────────────────────

  const openConversation = async (convId: string) => {
    setActiveConvId(convId);
    setScreen("chat");
    await fetchConversation(convId);
  };

  const openNewMessage = async () => {
    await fetchContacts();
    setScreen("contacts");
    setContactSearch("");
  };

  const startConversation = async (contact: Contact) => {
    setScreen("new");
    setActiveConv({
      id: "",
      participants: [contact],
      messages: [],
    });
    setMsgText("");
  };

  const sendNewMessage = async (recipientId: string) => {
    if (!msgText.trim()) return;
    setSending(true);
    try {
      const { data } = await apiClient.post("/messages/conversations", {
        recipient_id: recipientId,
        body: msgText.trim(),
      });
      setActiveConvId(data.id);
      setActiveConv(data);
      setScreen("chat");
      setMsgText("");
      fetchConversations();
    } catch { /* ignore */ }
    setSending(false);
  };

  const sendReply = async () => {
    if (!msgText.trim() || !activeConvId) return;
    setSending(true);
    try {
      await apiClient.post(`/messages/conversations/${activeConvId}/messages`, {
        body: msgText.trim(),
      });
      setMsgText("");
      await fetchConversation(activeConvId);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    } catch { /* ignore */ }
    setSending(false);
  };

  // ── Screens ───────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  // ── Contact picker ────────────────────────────────────────────────────
  if (screen === "contacts") {
    const filtered = contacts.filter(
      (c) =>
        c.full_name.toLowerCase().includes(contactSearch.toLowerCase()) ||
        c.email.toLowerCase().includes(contactSearch.toLowerCase())
    );
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable onPress={() => setScreen("list")} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={22} color={colors.text} />
          </Pressable>
          <Text style={styles.headerTitle}>New Message</Text>
        </View>
        <TextInput
          style={styles.searchInput}
          placeholder="Search contacts..."
          placeholderTextColor={colors.muted}
          value={contactSearch}
          onChangeText={setContactSearch}
          selectionColor={colors.primary}
        />
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Pressable
              style={styles.contactRow}
              onPress={() => startConversation(item)}
            >
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{initial(item.full_name)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.contactName}>{item.full_name}</Text>
                <Text style={styles.contactRole}>
                  {ROLE_LABELS[item.role] ?? item.role} · {item.email}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.muted} />
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No contacts available</Text>
          }
        />
      </View>
    );
  }

  // ── New message compose ───────────────────────────────────────────────
  if (screen === "new" && activeConv) {
    const recipient = activeConv.participants[0];
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={90}
      >
        <View style={styles.header}>
          <Pressable onPress={() => setScreen("contacts")} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={22} color={colors.text} />
          </Pressable>
          <View style={styles.headerUser}>
            <Text style={styles.headerTitle}>{recipient.full_name}</Text>
            <Text style={styles.headerSub}>{ROLE_LABELS[recipient.role] ?? recipient.role}</Text>
          </View>
        </View>
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center", padding: 40 }}>
          <View style={[styles.avatarLg, shadow.primary]}>
            <Text style={styles.avatarLgText}>{initial(recipient.full_name)}</Text>
          </View>
          <Text style={[styles.contactName, { marginTop: 16, fontSize: 20 }]}>
            {recipient.full_name}
          </Text>
          <Text style={[styles.contactRole, { marginTop: 4 }]}>
            Start a conversation with {recipient.full_name.split(" ")[0]}
          </Text>
        </View>
        <View style={styles.inputBar}>
          <TextInput
            style={styles.msgInput}
            placeholder="Type a message..."
            placeholderTextColor={colors.muted}
            value={msgText}
            onChangeText={setMsgText}
            selectionColor={colors.primary}
            multiline
          />
          <Pressable
            style={[styles.sendBtn, !msgText.trim() && { opacity: 0.4 }]}
            onPress={() => sendNewMessage(recipient.id)}
            disabled={!msgText.trim() || sending}
          >
            {sending ? (
              <ActivityIndicator size="small" color={colors.white} />
            ) : (
              <Ionicons name="send" size={18} color={colors.white} />
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    );
  }

  // ── Chat thread ───────────────────────────────────────────────────────
  if (screen === "chat" && activeConv) {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={90}
      >
        <View style={styles.header}>
          <Pressable
            onPress={() => {
              setScreen("list");
              fetchConversations();
            }}
            style={styles.backBtn}
          >
            <Ionicons name="arrow-back" size={22} color={colors.text} />
          </Pressable>
          <View style={styles.headerUser}>
            <Text style={styles.headerTitle}>
              {activeConv.participants.map((p) => p.full_name).join(", ")}
            </Text>
            <Text style={styles.headerSub}>
              {activeConv.participants.map((p) => ROLE_LABELS[p.role] ?? p.role).join(" · ")}
            </Text>
          </View>
        </View>
        <FlatList
          ref={flatListRef}
          data={activeConv.messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: spacing.md, paddingBottom: 8 }}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: false })
          }
          renderItem={({ item }) => (
            <View style={styles.msgBubbleWrap}>
              <Text style={styles.msgSender}>
                {item.sender_name}{" "}
                <Text style={styles.msgTime}>· {timeAgo(item.created_at)}</Text>
              </Text>
              <View style={styles.msgBubble}>
                <Text style={styles.msgBody}>{item.body}</Text>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No messages yet. Say hello!</Text>
          }
        />
        <View style={styles.inputBar}>
          <TextInput
            style={styles.msgInput}
            placeholder="Type a message..."
            placeholderTextColor={colors.muted}
            value={msgText}
            onChangeText={setMsgText}
            selectionColor={colors.primary}
            multiline
          />
          <Pressable
            style={[styles.sendBtn, !msgText.trim() && { opacity: 0.4 }]}
            onPress={sendReply}
            disabled={!msgText.trim() || sending}
          >
            {sending ? (
              <ActivityIndicator size="small" color={colors.white} />
            ) : (
              <Ionicons name="send" size={18} color={colors.white} />
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    );
  }

  // ── Conversation list (default) ───────────────────────────────────────
  return (
    <View style={styles.container}>
      <View style={[styles.header, { justifyContent: "space-between" }]}>
        <Text style={styles.headerTitle}>Messages</Text>
        <Pressable style={styles.newBtn} onPress={openNewMessage}>
          <Ionicons name="create-outline" size={20} color={colors.white} />
        </Pressable>
      </View>
      <FlatList
        data={conversations}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
        renderItem={({ item }) => {
          const name = item.participants.map((p) => p.full_name).join(", ");
          return (
            <Pressable
              style={styles.convRow}
              onPress={() => openConversation(item.id)}
            >
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{initial(name)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <Text
                    style={[
                      styles.convName,
                      item.unread_count > 0 && { fontWeight: "700" },
                    ]}
                    numberOfLines={1}
                  >
                    {name}
                  </Text>
                  {item.last_message && (
                    <Text style={styles.convTime}>
                      {timeAgo(item.last_message.created_at)}
                    </Text>
                  )}
                </View>
                {item.last_message && (
                  <Text style={styles.convPreview} numberOfLines={1}>
                    {item.last_message.body}
                  </Text>
                )}
              </View>
              {item.unread_count > 0 && (
                <View style={styles.unreadBadge}>
                  <Text style={styles.unreadText}>{item.unread_count}</Text>
                </View>
              )}
            </Pressable>
          );
        }}
        ListEmptyComponent={
          <View style={{ alignItems: "center", padding: 48 }}>
            <Ionicons name="chatbubbles-outline" size={48} color={colors.muted} />
            <Text style={[styles.emptyText, { marginTop: 12 }]}>
              No conversations yet
            </Text>
            <Pressable style={styles.emptyBtn} onPress={openNewMessage}>
              <Text style={styles.emptyBtnText}>Start a conversation</Text>
            </Pressable>
          </View>
        }
      />
    </View>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    backgroundColor: colors.bgCard,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineLight,
    gap: 12,
  },
  headerTitle: { ...font.bold, fontSize: 18, color: colors.text },
  headerSub: { ...font.regular, fontSize: 12, color: colors.textSecondary },
  headerUser: { flex: 1 },
  backBtn: { padding: 4 },
  newBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  // ── Conversation list ──
  convRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineLight,
    gap: 12,
    backgroundColor: colors.bgCard,
  },
  convName: { ...font.semibold, fontSize: 15, color: colors.text, flex: 1 },
  convTime: { ...font.regular, fontSize: 11, color: colors.muted, marginLeft: 8 },
  convPreview: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  unreadBadge: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
    marginLeft: 8,
  },
  unreadText: { ...font.bold, fontSize: 11, color: colors.white },
  // ── Avatar ──
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { ...font.bold, fontSize: 17, color: colors.primary },
  avatarLg: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarLgText: { ...font.bold, fontSize: 28, color: colors.white },
  // ── Contact list ──
  searchInput: {
    margin: spacing.md,
    backgroundColor: colors.bgCard,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.line,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.text,
    ...font.regular,
  },
  contactRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineLight,
    gap: 12,
    backgroundColor: colors.bgCard,
  },
  contactName: { ...font.semibold, fontSize: 15, color: colors.text },
  contactRole: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 1 },
  // ── Chat messages ──
  msgBubbleWrap: { marginBottom: 14 },
  msgSender: { ...font.semibold, fontSize: 12, color: colors.textSecondary, marginBottom: 4 },
  msgTime: { ...font.regular, fontWeight: "400" },
  msgBubble: {
    backgroundColor: colors.bgCard,
    borderRadius: radius.lg,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.lineLight,
    maxWidth: "88%",
  },
  msgBody: { ...font.regular, fontSize: 15, color: colors.text, lineHeight: 22 },
  // ── Input bar ──
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 10,
    paddingBottom: Platform.OS === "ios" ? 28 : 10,
    borderTopWidth: 1,
    borderTopColor: colors.lineLight,
    backgroundColor: colors.bgCard,
    gap: 8,
  },
  msgInput: {
    flex: 1,
    backgroundColor: colors.bgInput,
    borderRadius: radius.xl,
    borderWidth: 1.5,
    borderColor: colors.line,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: colors.text,
    maxHeight: 100,
    ...font.regular,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  // ── Empty ──
  emptyText: { ...font.regular, fontSize: 14, color: colors.muted, textAlign: "center" },
  emptyBtn: {
    marginTop: 16,
    paddingVertical: 10,
    paddingHorizontal: 20,
    backgroundColor: colors.primaryDim,
    borderRadius: radius.full,
  },
  emptyBtnText: { ...font.semibold, fontSize: 14, color: colors.primary },
});
