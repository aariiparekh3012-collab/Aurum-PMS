import React, { useState } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { notificationsApi } from "../lib/api";
import { Card, Button, KPI, Loading, Toast } from "../components/ui";
import { FadeIn } from "../components/FadeIn";
import type { Activity } from "../lib/types";
import { colors, font, spacing, radius } from "../lib/theme";

const ENTITY_FILTERS = ["all", "application", "order", "trade", "client", "portfolio", "system"];

const ACTION_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  created: "add-circle-outline",
  approved: "checkmark-circle-outline",
  rejected: "close-circle-outline",
  submitted: "document-outline",
  filled: "checkmark-done-outline",
  settled: "swap-horizontal-outline",
  updated: "pencil-outline",
  provisioned: "shield-checkmark-outline",
  login: "log-in-outline",
};

function getIcon(action: string): keyof typeof Ionicons.glyphMap {
  const key = Object.keys(ACTION_ICONS).find((k) => action.toLowerCase().includes(k));
  return key ? ACTION_ICONS[key] : "ellipse-outline";
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  const days = Math.floor(hrs / 24);
  if (days < 30) return days + "d ago";
  return new Date(isoDate).toLocaleDateString("en-IN");
}

export function ActivityFeedScreen() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: "success" | "error" } | null>(null);
  const limit = 30;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["activity-feed", filter, page],
    queryFn: () => notificationsApi.feed(filter === "all" ? undefined : filter, limit, page * limit),
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["activity-feed"] });
      setToast({ msg: "All marked as read.", variant: "success" });
    },
  });

  const markOne = useMutation({
    mutationFn: (id: string) => notificationsApi.markOneRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["activity-feed"] }),
  });

  const items = data?.items || [];
  const total = data?.total || 0;
  const unread = data?.unread || 0;
  const totalPages = Math.ceil(total / limit);

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  return (
    <View style={styles.container}>
      <FadeIn>
        <Text style={styles.title}>Activity Feed</Text>
        <Text style={styles.subtitle}>Real-time log of platform activity</Text>
      </FadeIn>

      {/* KPIs */}
      <View style={styles.kpiRow}>
        <KPI value={total} label="Total Events" />
        <KPI value={unread} label="Unread" />
        {unread > 0 && (
          <Pressable onPress={() => markAll.mutate()} style={styles.markAllBtn}>
            <Ionicons name="checkmark-done-outline" size={16} color={colors.gold} />
            <Text style={styles.markAllText}>Mark all</Text>
          </Pressable>
        )}
      </View>

      {/* Filter chips */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {ENTITY_FILTERS.map((f) => (
          <Pressable
            key={f}
            onPress={() => { setFilter(f); setPage(0); }}
            style={[styles.chip, filter === f && styles.chipActive]}
          >
            <Text style={[styles.chipText, filter === f && styles.chipTextActive]}>
              {f}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* Activity list */}
      <FlatList
        data={items}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
        ListEmptyComponent={
          isLoading
            ? <Loading text="Loading activity..." />
            : <Text style={styles.empty}>No activity recorded yet.</Text>
        }
        renderItem={({ item: a }) => (
          <Pressable
            onPress={() => { if (!a.is_read) markOne.mutate(a.id); }}
            style={[styles.activityRow, !a.is_read && styles.activityUnread]}
          >
            <View style={[styles.iconCircle, !a.is_read && styles.iconCircleUnread]}>
              <Ionicons name={getIcon(a.action)} size={18} color={a.is_read ? colors.muted : colors.gold} />
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <View style={styles.actorRow}>
                <Text style={styles.actorName}>{a.actor_subject}</Text>
                <Text style={styles.actorRole}>({a.actor_role})</Text>
              </View>
              <Text style={styles.actionText}>
                <Text style={{ color: colors.gold }}>{a.action}</Text>
                <Text style={{ color: colors.muted }}> on </Text>
                <Text style={{ ...font.medium }}>{a.entity_type}</Text>
                {a.entity_id ? <Text style={styles.entityId}> {a.entity_id.slice(0, 8)}</Text> : null}
              </Text>
              {a.detail && <Text style={styles.detail}>{a.detail}</Text>}
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Text style={styles.timeText}>{timeAgo(a.created_at)}</Text>
              {!a.is_read && <View style={styles.unreadDot} />}
            </View>
          </Pressable>
        )}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <View style={styles.paginationRow}>
          <Pressable onPress={() => setPage(Math.max(0, page - 1))} disabled={page === 0}>
            <Ionicons name="chevron-back" size={20} color={page === 0 ? colors.line : colors.gold} />
          </Pressable>
          <Text style={styles.pageText}>Page {page + 1} of {totalPages}</Text>
          <Pressable onPress={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}>
            <Ionicons name="chevron-forward" size={20} color={page >= totalPages - 1 ? colors.line : colors.gold} />
          </Pressable>
        </View>
      )}

      {toast && <Toast message={toast.msg} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  title: { ...font.bold, fontSize: 24, color: colors.text, marginTop: spacing.sm },
  subtitle: { ...font.regular, fontSize: 13, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.md },
  kpiRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md, alignItems: "center" },
  markAllBtn: { flexDirection: "row", alignItems: "center", gap: 4, marginLeft: "auto" },
  markAllText: { ...font.medium, fontSize: 12, color: colors.gold },
  filterRow: { gap: 8, paddingBottom: spacing.md },
  chip: {
    paddingVertical: 8, paddingHorizontal: 16, borderRadius: radius.full,
    backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.line,
  },
  chipActive: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  chipText: { color: colors.textSecondary, fontSize: 13, ...font.medium, textTransform: "capitalize" },
  chipTextActive: { color: colors.gold },
  empty: { color: colors.muted, ...font.regular, textAlign: "center", paddingVertical: 40 },
  activityRow: {
    flexDirection: "row", alignItems: "flex-start",
    paddingVertical: 14, paddingHorizontal: 8,
    borderBottomWidth: 1, borderBottomColor: colors.line,
  },
  activityUnread: { backgroundColor: "rgba(212,175,55,0.04)" },
  iconCircle: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.line,
    alignItems: "center", justifyContent: "center",
  },
  iconCircleUnread: { backgroundColor: colors.goldDim, borderColor: colors.gold },
  actorRow: { flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 2 },
  actorName: { ...font.semibold, fontSize: 14, color: colors.text },
  actorRole: { ...font.regular, fontSize: 12, color: colors.muted },
  actionText: { ...font.regular, fontSize: 13, color: colors.text },
  entityId: { fontFamily: "monospace", fontSize: 11, color: colors.muted },
  detail: { ...font.regular, fontSize: 12, color: colors.muted, marginTop: 4 },
  timeText: { ...font.regular, fontSize: 11, color: colors.muted },
  unreadDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.gold, marginTop: 4 },
  paginationRow: {
    flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 16,
    paddingVertical: 12, borderTopWidth: 1, borderTopColor: colors.line,
  },
  pageText: { ...font.medium, fontSize: 13, color: colors.muted },
});
