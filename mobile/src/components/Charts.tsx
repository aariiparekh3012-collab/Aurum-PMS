import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Circle, Text as SvgText } from "react-native-svg";
import { colors, font, spacing } from "../lib/theme";

export interface Slice {
  label: string;
  value: number;
  color: string;
}

export function DonutChart({ data, size = 160 }: { data: Slice[]; size?: number }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = size / 2 - 16;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  return (
    <View style={chartStyles.donutWrap}>
      <Svg width={size} height={size} style={{ transform: [{ rotate: "-90deg" }] }}>
        <Circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={14} />
        {data.map((d) => {
          const len = (d.value / total) * circ;
          const el = (
            <Circle
              key={d.label}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={d.color}
              strokeWidth={14}
              strokeDasharray={`${len} ${circ - len}`}
              strokeDashoffset={-offset}
              strokeLinecap="round"
            />
          );
          offset += len;
          return el;
        })}
        <SvgText
          x={cx} y={cy}
          textAnchor="middle"
          alignmentBaseline="central"
          fill={colors.text}
          fontSize={22}
          fontWeight="700"
          rotation={90}
          origin={`${cx}, ${cy}`}
        >
          {total}
        </SvgText>
      </Svg>
      <View style={chartStyles.legend}>
        {data.map((d) => (
          <View key={d.label} style={chartStyles.legendItem}>
            <View style={[chartStyles.legendDot, { backgroundColor: d.color }]} />
            <Text style={chartStyles.legendLabel}>{d.label}</Text>
            <Text style={chartStyles.legendValue}>{d.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

export function BarChart({ data }: { data: Slice[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <View style={{ gap: 14 }}>
      {data.map((d) => (
        <View key={d.label}>
          <View style={chartStyles.barHeader}>
            <Text style={chartStyles.barLabel}>{d.label}</Text>
            <Text style={chartStyles.barValue}>{d.value}</Text>
          </View>
          <View style={chartStyles.barTrack}>
            <View
              style={[
                chartStyles.barFill,
                { width: `${(d.value / max) * 100}%`, backgroundColor: d.color },
              ]}
            />
          </View>
        </View>
      ))}
    </View>
  );
}

export const palette = (i: number) => colors.palette[i % colors.palette.length];

const chartStyles = StyleSheet.create({
  donutWrap: { flexDirection: "row", alignItems: "center", gap: 20 },
  legend: { flex: 1, gap: 8 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 3 },
  legendLabel: { color: colors.text, fontSize: 13, textTransform: "capitalize", ...font.regular, flex: 1 },
  legendValue: { color: colors.muted, fontSize: 12 },
  barHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4 },
  barLabel: { color: colors.text, fontSize: 13, textTransform: "capitalize", ...font.medium },
  barValue: { color: colors.muted, fontSize: 12 },
  barTrack: {
    height: 8,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 4,
    overflow: "hidden",
  },
  barFill: { height: "100%", borderRadius: 4 },
});
