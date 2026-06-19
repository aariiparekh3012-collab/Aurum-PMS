interface Step { label: string; key: string }

export default function Stepper({ steps, current }: { steps: Step[]; current: string }) {
  const idx = steps.findIndex((s) => s.key === current);
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
      {steps.map((step, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <div key={step.key} style={{ flex: 1, textAlign: "center" }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", margin: "0 auto 6px",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 600,
              background: done ? "var(--success)" : active ? "var(--primary)" : "var(--border)",
              color: done || active ? "#fff" : "var(--text-secondary)",
            }}>
              {done ? "✓" : i + 1}
            </div>
            <div style={{ fontSize: 12, fontWeight: active ? 600 : 400, color: active ? "var(--text)" : "var(--text-secondary)" }}>
              {step.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
