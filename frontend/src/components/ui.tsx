import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type {
  ReactNode,
  CSSProperties,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  ButtonHTMLAttributes,
} from "react";

/** Shared presentational components for the PMS design system. */

/* ════════════════════════════════ Card ════════════════════════════════ */

export function Card({ children, className = "", glass = false, style, onClick }: {
  children: ReactNode; className?: string; glass?: boolean; style?: CSSProperties; onClick?: () => void;
}) {
  return <div className={`card ${glass ? "card--glass" : ""} ${className}`} style={style} onClick={onClick}>{children}</div>;
}

/* ════════════════════════════════ Button ══════════════════════════════ */

export function Button({ children, variant = "default", block, loading, ...rest }: {
  children: ReactNode; variant?: "default" | "primary" | "ghost" | "danger";
  block?: boolean; loading?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = variant === "default" ? "" : `btn--${variant}`;
  return (
    <button className={`btn ${cls} ${block ? "btn--block" : ""}`} disabled={loading || rest.disabled} {...rest}>
      {loading ? <span className="spinner" /> : children}
    </button>
  );
}

/* ════════════════════════════════ Fields ══════════════════════════════ */

export function Field({ label, error, ...rest }: {
  label: string; error?: string;
} & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      <input className={`input ${error ? "input--error" : ""}`} {...rest} />
      {error && <div className="field__error">{error}</div>}
    </div>
  );
}

export function SelectField({ label, error, children, ...rest }: {
  label: string; error?: string; children: ReactNode;
} & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      <select className="select" {...rest}>{children}</select>
      {error && <div className="field__error">{error}</div>}
    </div>
  );
}

/* ════════════════════════════════ StatusBadge ═════════════════════════ */

const STATUS_VARIANT: Record<string, string> = {
  active: "success", ready: "success", agreement_signed: "success", kyc_verified: "success",
  under_review: "warning", agreement_pending: "warning", risk_profiled: "info",
  kyc_pending: "info", draft: "info",
  rejected: "danger", kyc_rejected: "danger", dormant: "warning", closed: "danger",
  approved: "success", pending_approval: "warning", filled: "success", cancelled: "danger",
  new: "info",
};

export function StatusBadge({ status }: { status: string }) {
  const v = STATUS_VARIANT[status] ?? "gold";
  return <span className={`badge badge--${v}`}>{status.replace(/_/g, " ")}</span>;
}

/* ════════════════════════════════ Stepper ═════════════════════════════ */

export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="stepper">
      {steps.map((label, i) => {
        const state = i < current ? "step--done" : i === current ? "step--active" : "";
        return (
          <div className={`step ${state}`} key={label}>
            <div className="step__dot">{i < current ? "✓" : i + 1}</div>
            <div className="step__label">{label}</div>
            {i < steps.length - 1 && <div className="step__line" />}
          </div>
        );
      })}
    </div>
  );
}

/* ════════════════════════════════ KPI ═════════════════════════════════ */

export function KPI({ value, label }: { value: ReactNode; label: string }) {
  return (
    <Card glass className="kpi">
      <div className="kpi__value">{value}</div>
      <div className="kpi__label">{label}</div>
    </Card>
  );
}

/* ════════════════════════════════ Toast (standalone) ══════════════════ */

export function Toast({ message, variant = "error", duration = 4000, onDismiss }: {
  message: string; variant?: "error" | "success"; duration?: number; onDismiss?: () => void;
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onDismiss]);

  if (!visible) return null;

  return (
    <div className={`toast toast--${variant}`} onClick={() => { setVisible(false); onDismiss?.(); }}>
      {variant === "success" ? "✓" : "⚠"} {message}
    </div>
  );
}

/* ════════════════════════════════ Toast Provider (global) ═════════════ */

interface ToastItem {
  id: number;
  message: string;
  variant: "success" | "error";
}

interface ToastCtx {
  success: (msg: string) => void;
  error: (msg: string) => void;
}

const ToastContext = createContext<ToastCtx>({
  success: () => {},
  error: () => {},
});

export const useToast = () => useContext(ToastContext);

let _toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, variant: "success" | "error") => {
    const id = ++_toastId;
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const success = useCallback((msg: string) => push(msg, "success"), [push]);
  const error = useCallback((msg: string) => push(msg, "error"), [push]);

  return (
    <ToastContext.Provider value={{ success, error }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast toast--${t.variant}`}
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
          >
            {t.variant === "success" ? "✓" : "⚠"} {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ════════════════════════════════ ConfirmDialog ═══════════════════════ */

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "primary",
  loading = false,
  children,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
  loading?: boolean;
  children?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (open) {
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape") onCancel();
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginBottom: 8 }}>{title}</h3>
        {message && <p className="muted" style={{ marginBottom: 16, lineHeight: 1.6 }}>{message}</p>}
        {children && <div style={{ marginBottom: 16 }}>{children}</div>}
        <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onCancel} disabled={loading}>{cancelLabel}</Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════ Skeleton loaders ════════════════════ */

export function Skeleton({ width, height = 16, rounded = false, style }: {
  width?: string | number; height?: number; rounded?: boolean; style?: CSSProperties;
}) {
  return (
    <div
      className="skeleton"
      style={{
        width: width ?? "100%",
        height,
        borderRadius: rounded ? "50%" : 6,
        ...style,
      }}
    />
  );
}

// Stable widths — avoids Math.random() in render (StrictMode double-invoke flash)
const SKELETON_WIDTHS = ["25%", "20%", "22%", "18%", "15%", "20%", "17%", "23%"];

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <div className="row" style={{ gap: 16, padding: "14px 0", borderBottom: "1px solid var(--line)" }}>
      {Array.from({ length: cols }, (_, i) => (
        <Skeleton key={i} height={14} width={i === 0 ? "30%" : SKELETON_WIDTHS[i % SKELETON_WIDTHS.length]} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div>
      {Array.from({ length: rows }, (_, i) => (
        <SkeletonRow key={i} cols={cols} />
      ))}
    </div>
  );
}

export function SkeletonKPIs({ count = 4 }: { count?: number }) {
  return (
    <div className="kpis" style={{ marginBottom: 24 }}>
      {Array.from({ length: count }, (_, i) => (
        <Card glass key={i} className="kpi" style={{ padding: 20 }}>
          <Skeleton height={32} width="60%" style={{ marginBottom: 8 }} />
          <Skeleton height={12} width="40%" />
        </Card>
      ))}
    </div>
  );
}

/* ════════════════════════════════ Breadcrumb ══════════════════════════ */

export interface Crumb {
  label: string;
  to?: string;
}

export function Breadcrumb({ items, onNavigate }: {
  items: Crumb[];
  onNavigate: (to: string) => void;
}) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((crumb, i) => (
        <span key={i}>
          {i > 0 && <span className="breadcrumb__sep">/</span>}
          {crumb.to && i < items.length - 1 ? (
            <button className="breadcrumb__link" onClick={() => onNavigate(crumb.to!)}>
              {crumb.label}
            </button>
          ) : (
            <span className="breadcrumb__current">{crumb.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
