import React, { useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { colors, radius, spacing, font, shadow } from "../lib/theme";
import type { ViewStyleProp } from "../lib/rnStyleProp";

// ── Card ──
export function Card({
  children,
  glass,
  style,
  onPress,
}: {
  children: React.ReactNode;
  glass?: boolean;
  style?: ViewStyleProp;
  onPress?: () => void;
}) {
  const inner = (
    <View
      style={[
        styles.card,
        glass && styles.cardGlass,
        shadow.card,
        style,
      ]}
    >
      {children}
    </View>
  );
  return onPress ? (
    <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}>
      {inner}
    </Pressable>
  ) : inner;
}

// ── Button ──
export function Button({
  children,
  variant = "primary",
  block,
  loading,
  disabled,
  onPress,
  style,
}: {
  children: React.ReactNode;
  variant?: "primary" | "ghost" | "danger";
  block?: boolean;
  loading?: boolean;
  disabled?: boolean;
  onPress?: () => void;
  style?: ViewStyle;
}) {
  const isDisabled = disabled || loading;

  const handlePress = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.();
  };

  if (variant === "primary") {
    return (
      <Pressable
        onPress={handlePress}
        disabled={isDisabled}
        style={({ pressed }) => ({
          opacity: isDisabled ? 0.5 : pressed ? 0.85 : 1,
          borderRadius: radius.full,
          overflow: "hidden",
          alignSelf: block ? "stretch" : "auto",
          ...style,
        })}
      >
        <LinearGradient
          colors={["#ec4899", "#f97394", "#ffa56b"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0.5 }}
          style={[styles.btn, shadow.primary]}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={[styles.btnText, { color: colors.white }]}>{children}</Text>
          )}
        </LinearGradient>
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={handlePress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.btn,
        variant === "ghost" && styles.btnGhost,
        variant === "danger" && styles.btnDanger,
        { opacity: isDisabled ? 0.5 : pressed ? 0.7 : 1 },
        block && { alignSelf: "stretch" as const },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "danger" ? colors.white : colors.primary} size="small" />
      ) : (
        <Text
          style={[
            styles.btnText,
            variant === "ghost" && { color: colors.primaryHover },
            variant === "danger" && { color: colors.white },
          ]}
        >
          {children}
        </Text>
      )}
    </Pressable>
  );
}

// ── Field ──
export function Field({
  label,
  error,
  ...rest
}: { label: string; error?: string } & TextInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, error && styles.inputError]}
        placeholderTextColor={colors.muted}
        selectionColor={colors.primary}
        {...rest}
      />
      {error ? <Text style={styles.fieldError}>{error}</Text> : null}
    </View>
  );
}

// ── Picker-style select (simplified) ──
export function SelectField({
  label,
  options,
  value,
  onValueChange,
  error,
}: {
  label: string;
  options: { label: string; value: string }[];
  value: string;
  onValueChange: (v: string) => void;
  error?: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.selectRow}>
        {options.map((opt) => (
          <Pressable
            key={opt.value}
            onPress={() => onValueChange(opt.value)}
            style={[
              styles.selectChip,
              value === opt.value && styles.selectChipActive,
            ]}
          >
            <Text
              style={[
                styles.selectChipText,
                value === opt.value && styles.selectChipTextActive,
              ]}
            >
              {opt.label}
            </Text>
          </Pressable>
        ))}
      </View>
      {error ? <Text style={styles.fieldError}>{error}</Text> : null}
    </View>
  );
}

// ── Status Badge ──
const STATUS_COLORS: Record<string, string> = {
  active: colors.success,
  ready: colors.success,
  agreement_signed: colors.success,
  kyc_verified: colors.success,
  approved: colors.success,
  filled: colors.success,
  under_review: colors.warning,
  agreement_pending: colors.warning,
  pending_approval: colors.warning,
  risk_profiled: colors.info,
  kyc_pending: colors.info,
  draft: colors.info,
  new: colors.info,
  rejected: colors.danger,
  kyc_rejected: colors.danger,
  cancelled: colors.danger,
  dormant: colors.warning,
  closed: colors.danger,
};

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? colors.gold;
  return (
    <View style={[styles.badge, { backgroundColor: color + "18" }]}>
      <Text style={[styles.badgeText, { color }]}>
        {status.replace(/_/g, " ")}
      </Text>
    </View>
  );
}

// ── KPI Card ──
export function KPI({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <Card glass style={styles.kpi}>
      <Text style={styles.kpiValue}>{value}</Text>
      <Text style={styles.kpiLabel}>{label}</Text>
    </Card>
  );
}

// ── Toast ──
export function Toast({
  message,
  variant = "error",
  onDismiss,
}: {
  message: string;
  variant?: "error" | "success";
  onDismiss?: () => void;
}) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 300, useNativeDriver: true }),
      Animated.delay(3000),
      Animated.timing(opacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => onDismiss?.());
  }, []);

  const bg = variant === "success" ? colors.successLight : colors.dangerLight;
  const border = variant === "success" ? colors.success : colors.danger;
  const textColor = variant === "success" ? colors.success : colors.danger;

  return (
    <Animated.View
      style={[
        styles.toast,
        { opacity, backgroundColor: bg, borderColor: border, borderWidth: 1.5 },
      ]}
    >
      <Text style={[styles.toastText, { color: textColor }]}>
        {variant === "success" ? "✓ " : "⚠ "}
        {message}
      </Text>
    </Animated.View>
  );
}

// ── Stepper ──
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <View style={styles.stepper}>
      {steps.map((label, i) => (
        <View key={label} style={styles.stepItem}>
          <View
            style={[
              styles.stepDot,
              i < current && styles.stepDotDone,
              i === current && styles.stepDotActive,
            ]}
          >
            <Text style={[styles.stepDotText, i <= current && { color: colors.white }]}>
              {i < current ? "✓" : `${i + 1}`}
            </Text>
          </View>
          <Text
            style={[
              styles.stepLabel,
              i <= current && { color: colors.text },
            ]}
          >
            {label}
          </Text>
          {i < steps.length - 1 && (
            <View style={[styles.stepLine, i < current && styles.stepLineDone]} />
          )}
        </View>
      ))}
    </View>
  );
}

// ── Loading Spinner ──
export function Loading({ text }: { text?: string }) {
  return (
    <View style={styles.loading}>
      <ActivityIndicator size="large" color={colors.primary} />
      {text && <Text style={styles.loadingText}>{text}</Text>}
    </View>
  );
}

// ── Styles ──
const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1.5,
    borderColor: colors.lineLight,
  },
  cardGlass: {
    backgroundColor: colors.bgCardGlass,
    borderColor: colors.lineLight,
  },
  btn: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: radius.full,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  btnGhost: {
    backgroundColor: colors.bgCard,
    borderWidth: 1.5,
    borderColor: colors.line,
  },
  btnDanger: {
    backgroundColor: colors.danger,
  },
  btnText: {
    ...font.bold,
    fontSize: 15,
    color: colors.text,
  },
  field: { marginBottom: spacing.md },
  label: {
    ...font.semibold,
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.line,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    fontSize: 16,
    ...font.regular,
  },
  inputError: { borderColor: colors.danger },
  fieldError: { color: colors.danger, fontSize: 12, marginTop: 4 },
  selectRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  selectChip: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: radius.full,
    backgroundColor: colors.bgInput,
    borderWidth: 1.5,
    borderColor: colors.line,
  },
  selectChipActive: {
    backgroundColor: colors.primaryDim,
    borderColor: colors.primary,
  },
  selectChipText: { color: colors.textSecondary, fontSize: 14, ...font.medium },
  selectChipTextActive: { color: colors.primary },
  badge: {
    alignSelf: "flex-start",
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: radius.full,
  },
  badgeText: { fontSize: 12, ...font.bold, textTransform: "capitalize" },
  kpi: { flex: 1, alignItems: "center", padding: spacing.md },
  kpiValue: { ...font.bold, fontSize: 26, color: colors.text },
  kpiLabel: { ...font.regular, fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  toast: {
    position: "absolute",
    bottom: 100,
    left: 20,
    right: 20,
    padding: spacing.md,
    borderRadius: radius.md,
    zIndex: 999,
  },
  toastText: { ...font.semibold, fontSize: 14, textAlign: "center" },
  stepper: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.lg,
    paddingHorizontal: spacing.sm,
  },
  stepItem: { alignItems: "center", flex: 1 },
  stepDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primaryLight,
    borderWidth: 2,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  stepDotDone: { backgroundColor: colors.primary, borderColor: colors.primary },
  stepDotActive: { borderColor: colors.primary, backgroundColor: colors.primaryDim },
  stepDotText: { color: colors.textSecondary, fontSize: 13, ...font.semibold },
  stepLabel: { fontSize: 11, color: colors.muted, ...font.medium, textAlign: "center" },
  stepLine: {
    position: "absolute",
    top: 15,
    left: "60%",
    right: "-40%",
    height: 2,
    backgroundColor: colors.line,
  },
  stepLineDone: { backgroundColor: colors.primary },
  loading: { flex: 1, alignItems: "center", justifyContent: "center", padding: 40 },
  loadingText: { color: colors.textSecondary, marginTop: 12, ...font.regular },
});
