import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { messagingApi } from "./api";
import type { Contact, Conversation } from "./api";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  compliance: "Compliance",
  rm: "Relationship Manager",
  relationship_manager: "Relationship Manager",
  investor: "Investor",
};

function roleBadge(role: string) {
  return ROLE_LABELS[role] ?? role;
}

function timeAgo(iso: string) {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function initial(name: string) {
  return name?.[0]?.toUpperCase() ?? "?";
}

export function MessagesPage() {
  const qc = useQueryClient();
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [newMsgText, setNewMsgText] = useState("");
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [composeText, setComposeText] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const msgEndRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: messagingApi.conversations,
    refetchInterval: 8000,
  });
  const { data: contacts = [] } = useQuery({
    queryKey: ["contacts"],
    queryFn: messagingApi.contacts,
  });
  const { data: activeConv } = useQuery({
    queryKey: ["conversation", activeConvId],
    queryFn: () => messagingApi.conversation(activeConvId!),
    enabled: !!activeConvId,
    refetchInterval: 5000,
  });

  // Mutations
  const sendMutation = useMutation({
    mutationFn: (body: string) => messagingApi.sendMessage(activeConvId!, body),
    onSuccess: () => {
      setNewMsgText("");
      qc.invalidateQueries({ queryKey: ["conversation", activeConvId] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  const startMutation = useMutation({
    mutationFn: ({ recipientId, body }: { recipientId: string; body: string }) =>
      messagingApi.startConversation(recipientId, body),
    onSuccess: (data) => {
      setActiveConvId(data.id);
      setShowNewMessage(false);
      setSelectedContact(null);
      setComposeText("");
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  // Auto-scroll to bottom of messages
  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages]);

  function convDisplayName(conv: Conversation) {
    const others = conv.participants;
    if (others.length <= 2) {
      const other = others.find(
        (p) =>
          conv.last_message && p.id !== conv.last_message.sender_id
            ? true
            : others.indexOf(p) === 1
      );
      return other?.full_name ?? others[0]?.full_name ?? "Conversation";
    }
    return others.map((p) => p.full_name.split(" ")[0]).join(", ");
  }

  const filteredContacts = contacts.filter(
    (c) =>
      c.full_name.toLowerCase().includes(contactSearch.toLowerCase()) ||
      c.email.toLowerCase().includes(contactSearch.toLowerCase())
  );

  const handleSend = () => {
    const text = newMsgText.trim();
    if (!text || !activeConvId) return;
    sendMutation.mutate(text);
  };

  const handleStartConversation = () => {
    const text = composeText.trim();
    if (!text || !selectedContact) return;
    startMutation.mutate({ recipientId: selectedContact.id, body: text });
  };

  return (
    <div>
      <div className="page-header">
        <h1>Messages</h1>
        <button
          className="btn btn-primary"
          onClick={() => {
            setShowNewMessage(true);
            setActiveConvId(null);
          }}
        >
          + New Message
        </button>
      </div>

      <div style={{ display: "flex", gap: 20, height: "calc(100vh - 180px)" }}>
        {/* ── Conversation list ─────────────────────────────── */}
        <div
          className="card"
          style={{
            width: 320,
            minWidth: 320,
            padding: 0,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              padding: "16px 16px 12px",
              borderBottom: "1px solid var(--border)",
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Conversations
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {conversations.length === 0 && (
              <div
                style={{
                  padding: 32,
                  textAlign: "center",
                  color: "var(--text-secondary)",
                  fontSize: 14,
                }}
              >
                No conversations yet.
                <br />
                Start one with the button above.
              </div>
            )}
            {conversations.map((conv) => {
              const isActive = conv.id === activeConvId;
              return (
                <button
                  key={conv.id}
                  onClick={() => {
                    setActiveConvId(conv.id);
                    setShowNewMessage(false);
                  }}
                  style={{
                    display: "flex",
                    gap: 12,
                    alignItems: "center",
                    width: "100%",
                    padding: "14px 16px",
                    border: "none",
                    borderBottom: "1px solid var(--border)",
                    background: isActive
                      ? "linear-gradient(135deg, rgba(236,72,153,0.08), rgba(236,72,153,0.03))"
                      : "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "background 0.15s",
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 20,
                      background: isActive
                        ? "linear-gradient(135deg, #ec4899, #db2777)"
                        : "var(--bg-elevated)",
                      color: isActive ? "#fff" : "var(--primary)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: 15,
                      flexShrink: 0,
                    }}
                  >
                    {initial(convDisplayName(conv))}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: conv.unread_count > 0 ? 700 : 500,
                          fontSize: 14,
                          color: "var(--text)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {convDisplayName(conv)}
                      </span>
                      {conv.last_message && (
                        <span
                          style={{
                            fontSize: 11,
                            color: "var(--text-secondary)",
                            flexShrink: 0,
                            marginLeft: 8,
                          }}
                        >
                          {timeAgo(conv.last_message.created_at)}
                        </span>
                      )}
                    </div>
                    {conv.last_message && (
                      <div
                        style={{
                          fontSize: 13,
                          color: "var(--text-secondary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          marginTop: 2,
                        }}
                      >
                        {conv.last_message.body}
                      </div>
                    )}
                  </div>
                  {conv.unread_count > 0 && (
                    <span
                      style={{
                        background: "var(--primary)",
                        color: "#fff",
                        borderRadius: 10,
                        padding: "2px 8px",
                        fontSize: 11,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {conv.unread_count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Chat panel / new message ─────────────────────── */}
        <div
          className="card"
          style={{
            flex: 1,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {showNewMessage ? (
            /* ── New message composer ─── */
            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--border)",
                  fontWeight: 600,
                  fontSize: 15,
                }}
              >
                New Message
              </div>
              <div style={{ padding: 20, flex: 1, overflowY: "auto" }}>
                <label
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: "var(--text-secondary)",
                    display: "block",
                    marginBottom: 8,
                  }}
                >
                  To:
                </label>
                {selectedContact ? (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 14px",
                      background: "var(--bg-elevated)",
                      borderRadius: 10,
                      marginBottom: 20,
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: 16,
                        background: "linear-gradient(135deg, #ec4899, #db2777)",
                        color: "#fff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: 700,
                        fontSize: 13,
                      }}
                    >
                      {initial(selectedContact.full_name)}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>
                        {selectedContact.full_name}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                        {roleBadge(selectedContact.role)}
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedContact(null)}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--text-secondary)",
                        fontSize: 18,
                      }}
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <div>
                    <input
                      className="form-input"
                      placeholder="Search contacts..."
                      value={contactSearch}
                      onChange={(e) => setContactSearch(e.target.value)}
                      style={{ marginBottom: 12 }}
                    />
                    <div
                      style={{
                        maxHeight: 240,
                        overflowY: "auto",
                        border: "1px solid var(--border)",
                        borderRadius: 10,
                      }}
                    >
                      {filteredContacts.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => {
                            setSelectedContact(c);
                            setContactSearch("");
                          }}
                          style={{
                            display: "flex",
                            gap: 10,
                            alignItems: "center",
                            width: "100%",
                            padding: "10px 14px",
                            border: "none",
                            borderBottom: "1px solid var(--border)",
                            background: "transparent",
                            cursor: "pointer",
                            textAlign: "left",
                          }}
                        >
                          <div
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: 16,
                              background: "var(--bg-elevated)",
                              color: "var(--primary)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontWeight: 700,
                              fontSize: 13,
                            }}
                          >
                            {initial(c.full_name)}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>
                              {c.full_name}
                            </div>
                            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                              {roleBadge(c.role)} · {c.email}
                            </div>
                          </div>
                        </button>
                      ))}
                      {filteredContacts.length === 0 && (
                        <div
                          style={{
                            padding: 20,
                            textAlign: "center",
                            color: "var(--text-secondary)",
                            fontSize: 13,
                          }}
                        >
                          No contacts found
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {selectedContact && (
                  <div style={{ marginTop: 16 }}>
                    <label
                      style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: "var(--text-secondary)",
                        display: "block",
                        marginBottom: 8,
                      }}
                    >
                      Message:
                    </label>
                    <textarea
                      className="form-input"
                      rows={4}
                      placeholder="Type your message..."
                      value={composeText}
                      onChange={(e) => setComposeText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleStartConversation();
                        }
                      }}
                      style={{ resize: "vertical" }}
                    />
                    <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
                      <button
                        className="btn btn-primary"
                        onClick={handleStartConversation}
                        disabled={!composeText.trim() || startMutation.isPending}
                      >
                        {startMutation.isPending ? "Sending..." : "Send Message"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : activeConv ? (
            /* ── Chat thread ─── */
            <>
              <div
                style={{
                  padding: "14px 20px",
                  borderBottom: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 18,
                    background: "linear-gradient(135deg, #ec4899, #db2777)",
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: 14,
                  }}
                >
                  {initial(activeConv.participants[0]?.full_name ?? "")}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>
                    {activeConv.participants.map((p) => p.full_name).join(", ")}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    {activeConv.participants.map((p) => roleBadge(p.role)).join(" · ")}
                  </div>
                </div>
              </div>
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "20px 20px 10px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                {activeConv.messages.map((msg) => {
                  return (
                    <div key={msg.id}>
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-secondary)",
                          marginBottom: 4,
                          fontWeight: 600,
                        }}
                      >
                        {msg.sender_name}{" "}
                        <span style={{ fontWeight: 400 }}>
                          · {timeAgo(msg.created_at)}
                        </span>
                      </div>
                      <div
                        style={{
                          padding: "10px 14px",
                          borderRadius: 12,
                          background: "var(--bg-elevated)",
                          fontSize: 14,
                          lineHeight: 1.5,
                          maxWidth: "85%",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {msg.body}
                      </div>
                    </div>
                  );
                })}
                <div ref={msgEndRef} />
              </div>
              <div
                style={{
                  padding: "12px 20px",
                  borderTop: "1px solid var(--border)",
                  display: "flex",
                  gap: 10,
                }}
              >
                <input
                  className="form-input"
                  style={{ flex: 1 }}
                  placeholder="Type a message..."
                  value={newMsgText}
                  onChange={(e) => setNewMsgText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <button
                  className="btn btn-primary"
                  onClick={handleSend}
                  disabled={!newMsgText.trim() || sendMutation.isPending}
                >
                  Send
                </button>
              </div>
            </>
          ) : (
            /* ── Empty state ─── */
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                gap: 12,
                color: "var(--text-secondary)",
              }}
            >
              <svg
                width={48}
                height={48}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ opacity: 0.5 }}
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <div style={{ fontSize: 15, fontWeight: 500 }}>
                Select a conversation or start a new one
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
