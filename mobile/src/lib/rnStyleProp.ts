import type { ViewStyle } from "react-native";

/**
 * Minimal stand-in for StyleProp<ViewStyle>.
 * Defined in a plain .ts file to avoid TSX-parser issues with array type syntax.
 */
export type ViewStyleProp = ViewStyle | (ViewStyle | false | null | undefined)[];
