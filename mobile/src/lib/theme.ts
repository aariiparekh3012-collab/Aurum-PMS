/** Aurum PMS — "Petal & Cream" design system (matches web) */

export const colors = {
  // Backgrounds
  bg: "#fff6f1",
  bgCard: "#fffdfc",
  bgCardGlass: "rgba(255, 253, 252, 0.75)",
  bgElevated: "#fdeef3",
  bgInput: "#fff9f7",

  // Brand (pink)
  primary: "#ec4899",
  primaryHover: "#db2777",
  primaryLight: "#fde5f0",
  primaryDim: "rgba(236, 72, 153, 0.12)",

  // Accent (rose-gold, for highlights/charts)
  gold: "#e79a86",
  goldLight: "#f3c9bd",
  goldDim: "rgba(231, 154, 134, 0.15)",

  // Text
  text: "#43273c",
  textSecondary: "#9b6f86",
  muted: "#bb97aa",

  // Semantic
  success: "#1fa97f",
  successLight: "#e3f8f0",
  warning: "#f59e0b",
  warningLight: "#fdf2dc",
  danger: "#e5484d",
  dangerLight: "#fdeaea",
  info: "#3a63c4",
  infoLight: "#e8eefc",

  // Lines / borders
  line: "#f4d6e2",
  lineLight: "#fbe9f0",

  // Chart palette
  palette: ["#ec4899", "#f97394", "#e79a86", "#3a63c4", "#1fa97f"],

  // White (for text on colored bg)
  white: "#ffffff",
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
    shadowColor: "#ec4899",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 14,
    elevation: 6,
  },
  primary: {
    shadowColor: "#ec4899",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 10,
  },
  // Keep "gold" alias for backward compat — now references primary shadow
  gold: {
    shadowColor: "#ec4899",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 10,
  },
};
