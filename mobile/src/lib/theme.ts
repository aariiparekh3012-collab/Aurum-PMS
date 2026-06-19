/** Aurum PMS dark + gold design system */

export const colors = {
  // Backgrounds
  bg: "#0a0e17",
  bgCard: "#131926",
  bgCardGlass: "rgba(19, 25, 38, 0.75)",
  bgElevated: "#1a2235",
  bgInput: "#0d1220",

  // Brand
  gold: "#d4af37",
  goldLight: "#f0d27a",
  goldDim: "rgba(212, 175, 55, 0.15)",

  // Text
  text: "#eef2f8",
  textSecondary: "#8896ab",
  muted: "#5a6a80",

  // Semantic
  success: "#34d399",
  warning: "#fbbf24",
  danger: "#f87171",
  info: "#60a5fa",

  // Lines
  line: "rgba(255, 255, 255, 0.06)",
  lineLight: "rgba(255, 255, 255, 0.12)",

  // Chart palette
  palette: ["#d4af37", "#f0d27a", "#9aa7bd", "#60a5fa", "#34d399"],
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 999,
} as const;

export const font = {
  regular: { fontFamily: "System", fontWeight: "400" as const },
  medium: { fontFamily: "System", fontWeight: "500" as const },
  semibold: { fontFamily: "System", fontWeight: "600" as const },
  bold: { fontFamily: "System", fontWeight: "700" as const },
};

export const shadow = {
  card: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  gold: {
    shadowColor: "#d4af37",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 12,
  },
};
