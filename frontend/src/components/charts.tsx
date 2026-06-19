/** Dependency-free SVG charts for the PMS design system.
 *  All charts are pure SVG — no external charting library. */

export interface Slice {
  label: string;
  value: number;
  color: string;
}

export interface DataPoint {
  x: string;
  y: number;
}

export interface LineSeries {
  label: string;
  color: string;
  data: DataPoint[];
}

const GOLD = ["#d4af37", "#f0d27a", "#9aa7bd", "#60a5fa", "#34d399", "#f87171", "#c084fc", "#fbbf24"];

export const palette = (i: number) => GOLD[i % GOLD.length];

/* ════════════════════════════════ DonutChart ══════════════════════════ */

export function DonutChart({ data, size = 168 }: { data: Slice[]; size?: number }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = size / 2 - 16;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className="row" style={{ gap: 24, alignItems: "center" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f4d6e2" strokeWidth={16} />
        {data.map((d) => {
          const len = (d.value / total) * circ;
          const el = (
            <circle
              key={d.label}
              cx={cx} cy={cy} r={r} fill="none"
              stroke={d.color} strokeWidth={16}
              strokeDasharray={`${len} ${circ - len}`}
              strokeDashoffset={-offset}
              style={{ transition: "stroke-dasharray .6s ease" }}
            />
          );
          offset += len;
          return el;
        })}
        <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central"
          transform={`rotate(90 ${cx} ${cy})`} fill="#eef2f8"
          style={{ font: "600 1.6rem Fraunces, serif" }}>
          {total}
        </text>
      </svg>
      <div>
        {data.map((d) => (
          <div className="row" key={d.label} style={{ gap: 8, marginBottom: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: d.color, display: "inline-block" }} />
            <span style={{ textTransform: "capitalize", fontSize: ".88rem" }}>{d.label}</span>
            <span className="faint" style={{ fontSize: ".82rem" }}>· {d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ════════════════════════════════ BarChart ════════════════════════════ */

export function BarChart({ data }: { data: Slice[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {data.map((d) => (
        <div key={d.label}>
          <div className="row row--between" style={{ marginBottom: 4 }}>
            <span style={{ textTransform: "capitalize", fontSize: ".85rem" }}>{d.label}</span>
            <span className="faint" style={{ fontSize: ".82rem" }}>{d.value}</span>
          </div>
          <div style={{ height: 8, background: "#f4d6e2", borderRadius: 4, overflow: "hidden" }}>
            <div style={{
              width: `${(d.value / max) * 100}%`, height: "100%", borderRadius: 4,
              background: `linear-gradient(90deg, ${d.color}, ${d.color}cc)`,
              transition: "width .6s ease",
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ════════════════════════════════ AreaChart ═══════════════════════════ */

export function AreaChart({
  data,
  width = 520,
  height = 200,
  color = "#d4af37",
  formatY = (v: number) => String(v),
  gradientId = "areaGrad",
}: {
  data: DataPoint[];
  width?: number;
  height?: number;
  color?: string;
  formatY?: (v: number) => string;
  gradientId?: string;
}) {
  if (data.length < 2) return <div className="empty">Not enough data for chart.</div>;

  const pad = { top: 20, right: 16, bottom: 28, left: 70 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;
  const vals = data.map((d) => d.y);
  const minY = Math.min(...vals);
  const maxY = Math.max(...vals);
  const rangeY = maxY - minY || 1;

  const pts = data.map((d, i) => ({
    x: pad.left + (i / (data.length - 1)) * w,
    y: pad.top + h - ((d.y - minY) / rangeY) * h,
    label: d.x,
    val: d.y,
  }));

  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaD = `${pathD} L ${pts[pts.length - 1].x.toFixed(1)} ${pad.top + h} L ${pts[0].x.toFixed(1)} ${pad.top + h} Z`;

  const gridLines = [0, 0.25, 0.5, 0.75, 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", maxWidth: width }}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.25} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {gridLines.map((t) => {
        const y = pad.top + h - t * h;
        const val = minY + t * rangeY;
        return (
          <g key={t}>
            <line x1={pad.left} y1={y} x2={pad.left + w} y2={y} stroke="#f4d6e2" />
            <text x={pad.left - 8} y={y + 4} textAnchor="end" fill="#9b6f86" fontSize="10">
              {formatY(val)}
            </text>
          </g>
        );
      })}
      <path d={areaD} fill={`url(#${gradientId})`} />
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Start + end dots */}
      <circle cx={pts[0].x} cy={pts[0].y} r={3} fill={color} />
      <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r={3} fill={color} />
      {/* X-axis labels */}
      {pts
        .filter((_, i) => i % Math.max(1, Math.floor(pts.length / 6)) === 0 || i === pts.length - 1)
        .map((p) => (
          <text key={p.label} x={p.x} y={pad.top + h + 16} textAnchor="middle" fill="#9b6f86" fontSize="9">
            {p.label}
          </text>
        ))}
    </svg>
  );
}

/* ════════════════════════════════ MultiLineChart ═════════════════════ */

export function MultiLineChart({
  series,
  width = 520,
  height = 220,
  formatY = (v: number) => String(v),
}: {
  series: LineSeries[];
  width?: number;
  height?: number;
  formatY?: (v: number) => string;
}) {
  if (series.length === 0 || series[0].data.length < 2) {
    return <div className="empty">Not enough data for chart.</div>;
  }

  const pad = { top: 20, right: 16, bottom: 36, left: 70 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;

  // Global min/max across all series
  const allVals = series.flatMap((s) => s.data.map((d) => d.y));
  const minY = Math.min(...allVals);
  const maxY = Math.max(...allVals);
  const rangeY = maxY - minY || 1;

  const maxLen = Math.max(...series.map((s) => s.data.length));
  const gridLines = [0, 0.25, 0.5, 0.75, 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", maxWidth: width }}>
      {/* Grid */}
      {gridLines.map((t) => {
        const y = pad.top + h - t * h;
        return (
          <g key={t}>
            <line x1={pad.left} y1={y} x2={pad.left + w} y2={y} stroke="#f4d6e2" />
            <text x={pad.left - 8} y={y + 4} textAnchor="end" fill="#9b6f86" fontSize="10">
              {formatY(minY + t * rangeY)}
            </text>
          </g>
        );
      })}

      {/* Lines */}
      {series.map((s) => {
        const pts = s.data.map((d, i) => ({
          x: pad.left + (i / (s.data.length - 1)) * w,
          y: pad.top + h - ((d.y - minY) / rangeY) * h,
        }));
        const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
        return (
          <g key={s.label}>
            <path d={pathD} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round"
              strokeDasharray={s === series[0] ? "none" : "6 3"} />
            <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r={3} fill={s.color} />
          </g>
        );
      })}

      {/* X-axis labels from first series */}
      {series[0].data
        .filter((_, i) => i % Math.max(1, Math.floor(maxLen / 6)) === 0 || i === maxLen - 1)
        .map((d, i) => {
          const x = pad.left + ((series[0].data.indexOf(d)) / (series[0].data.length - 1)) * w;
          return (
            <text key={i} x={x} y={pad.top + h + 16} textAnchor="middle" fill="#9b6f86" fontSize="9">
              {d.x}
            </text>
          );
        })}

      {/* Legend */}
      {series.map((s, i) => (
        <g key={s.label} transform={`translate(${pad.left + i * 140}, ${height - 8})`}>
          <line x1={0} y1={-3} x2={16} y2={-3} stroke={s.color} strokeWidth={2}
            strokeDasharray={i === 0 ? "none" : "6 3"} />
          <text x={20} y={0} fill="#9b6f86" fontSize="10">{s.label}</text>
        </g>
      ))}
    </svg>
  );
}

/* ════════════════════════════════ GaugeChart ═════════════════════════ */

export function GaugeChart({
  value,
  max = 100,
  label,
  size = 140,
  color,
}: {
  value: number;
  max?: number;
  label?: string;
  size?: number;
  color?: string;
}) {
  const cx = size / 2;
  const cy = size / 2 + 10;
  const r = size / 2 - 16;
  const startAngle = -210;
  const endAngle = 30;
  const totalAngle = endAngle - startAngle;
  const pct = Math.min(value / max, 1);
  const valueAngle = startAngle + pct * totalAngle;

  const getColor = () => {
    if (color) return color;
    if (pct < 0.33) return "#34d399";
    if (pct < 0.66) return "#fbbf24";
    return "#f87171";
  };

  const polarToCartesian = (angle: number) => {
    const rad = (angle * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const describeArc = (start: number, end: number) => {
    const s = polarToCartesian(start);
    const e = polarToCartesian(end);
    const largeArc = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} 1 ${e.x} ${e.y}`;
  };

  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <path d={describeArc(startAngle, endAngle)} fill="none" stroke="#f4d6e2" strokeWidth={10} strokeLinecap="round" />
      <path d={describeArc(startAngle, valueAngle)} fill="none" stroke={getColor()} strokeWidth={10} strokeLinecap="round"
        style={{ transition: "d .6s ease" }} />
      <text x={cx} y={cy - 4} textAnchor="middle" fill="#eef2f8" style={{ font: "600 1.4rem Fraunces, serif" }}>
        {value}
      </text>
      {label && (
        <text x={cx} y={cy + 16} textAnchor="middle" fill="#9b6f86" fontSize="10">
          {label}
        </text>
      )}
    </svg>
  );
}

/* ════════════════════════════════ Sparkline ══════════════════════════ */

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color = "#d4af37",
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const pts = data.map((v, i) => ({
    x: pad + (i / (data.length - 1)) * w,
    y: pad + h - ((v - min) / range) * h,
  }));

  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

/* ════════════════════════════════ HorizontalBarChart ═════════════════ */

export function HorizontalBarChart({ data, maxWidth = 500 }: { data: Slice[]; maxWidth?: number }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const total = data.reduce((s, d) => s + d.value, 0) || 1;

  return (
    <div style={{ display: "grid", gap: 10, maxWidth }}>
      {data.map((d) => (
        <div key={d.label} style={{ display: "grid", gridTemplateColumns: "100px 1fr 50px", gap: 12, alignItems: "center" }}>
          <span style={{ textTransform: "capitalize", fontSize: ".85rem", textAlign: "right" }}>{d.label}</span>
          <div style={{ height: 20, background: "#fbe9f0", borderRadius: 6, overflow: "hidden", position: "relative" }}>
            <div style={{
              width: `${(d.value / max) * 100}%`,
              height: "100%",
              borderRadius: 6,
              background: `linear-gradient(90deg, ${d.color}dd, ${d.color})`,
              transition: "width .6s ease",
            }} />
          </div>
          <span className="faint" style={{ fontSize: ".82rem" }}>{((d.value / total) * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}
