import type React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth, homeFor } from "../../lib/auth";
import { apiClient } from "../../lib/apiClient";
import { useAuth } from "../../contexts/AuthContext";
import { authApi } from "./api";
import { Button, Card, Field, SelectField, useToast } from "../../components/ui";

type View = "login" | "register" | "forgot" | "verify";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const COUNTRY_CODES = [
  { code: "+91", label: "IN +91", flag: "🇮🇳" },
  { code: "+1", label: "US +1", flag: "🇺🇸" },
] as const;

function validateEmail(v: string): string {
  if (!v) return "";
  if (!EMAIL_RE.test(v)) return "Invalid email — must be like name@company.com";
  return "";
}

type PasswordStrength = "none" | "weak" | "fair" | "strong" | "very-strong";

function getPasswordStrength(pw: string): { level: PasswordStrength; label: string; color: string; percent: number } {
  if (!pw) return { level: "none", label: "", color: "transparent", percent: 0 };
  let score = 0;
  if (pw.length >= 6) score++;
  if (pw.length >= 10) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;

  if (score <= 1) return { level: "weak", label: "Weak", color: "#ef4444", percent: 25 };
  if (score === 2) return { level: "fair", label: "Fair", color: "#f59e0b", percent: 50 };
  if (score === 3) return { level: "strong", label: "Strong", color: "#22c55e", percent: 75 };
  return { level: "very-strong", label: "Very Strong", color: "#10b981", percent: 100 };
}

export function LoginPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { refresh } = useAuth();
  const [view, setView] = useState<View>("login");

  // Login state
  const [email, setEmail] = useState("");
  const [emailErr, setEmailErr] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  // Register state
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regEmailErr, setRegEmailErr] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");
  const [regRole, setRegRole] = useState("investor");
  const [regPhone, setRegPhone] = useState("");
  const [regCountryCode, setRegCountryCode] = useState("+91");
  const [accessCode, setAccessCode] = useState("");
  const [showAccessCode, setShowAccessCode] = useState(false);

  // Verify (post-signup) state
  const [otpCode, setOtpCode] = useState("");
  const [otpMsg, setOtpMsg] = useState("");

  // Forgot state
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSent, setForgotSent] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const eErr = validateEmail(email);
    if (eErr) { setEmailErr(eErr); return; }
    setLoading(true);
    try {
      const data = await authApi.login({ email, password });
      auth.setTokens(data.access_token, data.refresh_token, data.expires_in, {
        subject: email,
        role: "",
        email,
      });
      const me = await authApi.me();
      auth.updateUser({
        role: me.role,
        id: me.id,
        full_name: me.full_name,
        email_verified: me.email_verified,
      });
      refresh();
      navigate(homeFor(me.role));
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const eErr = validateEmail(regEmail);
    if (eErr) { setRegEmailErr(eErr); return; }
    if (regPassword !== regConfirm) {
      toast.error("Passwords do not match");
      return;
    }
    if ((regRole === "rm" || regRole === "compliance" || regRole === "admin") && !accessCode.trim()) {
      setShowAccessCode(true);
      toast.error("Enter the access code for this role");
      return;
    }
    const fullPhone = regPhone.trim() ? regCountryCode + regPhone.trim() : undefined;
    setLoading(true);
    try {
      const data = await authApi.register({
        email: regEmail,
        password: regPassword,
        full_name: regName,
        role: regRole,
        phone: fullPhone,
        access_code: (regRole === "rm" || regRole === "compliance" || regRole === "admin") ? accessCode.trim() : undefined,
      });
      auth.setTokens(data.access_token, data.refresh_token, data.expires_in, {
        subject: regEmail,
        role: regRole,
        email: regEmail,
        full_name: regName,
      });
      refresh();
      toast.success("Account created — verify your email and phone.");
      setView("verify");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPhone = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.verifyPhone(otpCode.trim());
      toast.success("Phone verified!");
      navigate(homeFor(regRole || "investor"));
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setLoading(true);
    try {
      const res = await authApi.sendPhoneOtp(regPhone.trim() || undefined);
      setOtpMsg(res.message);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    const eErr = validateEmail(forgotEmail);
    if (eErr) { toast.error(eErr); return; }
    setLoading(true);
    try {
      await authApi.forgotPassword(forgotEmail);
      setForgotSent(true);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (role: "compliance" | "rm" | "investor") => {
    if (role === "investor") {
      setLoading(true);
      try {
        const data = await authApi.login({ email: "asha@example.com", password: "investor123" });
        auth.setTokens(data.access_token, data.refresh_token, data.expires_in, {
          subject: "asha@example.com",
          role: "investor",
          email: "asha@example.com",
        });
        const me = await authApi.me();
        auth.updateUser({ role: me.role, id: me.id, full_name: me.full_name });
        navigate(homeFor(me.role));
      } catch {
        toast.error("Demo investor account not seeded yet — run seed_demo.py first.");
      } finally {
        setLoading(false);
      }
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.post("/auth/token", { username: `demo.${role}`, role });
      const token: string = res.data.access_token;
      auth.setSession(token, { subject: `demo.${role}`, role });
      refresh();
      navigate(homeFor(role));
    } catch {
      toast.error("Dev token unavailable — make sure ENVIRONMENT is not production.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="center" style={{ marginBottom: 28 }}>
          <div
            className="brand__mark"
            style={{
              margin: "0 auto 16px",
              width: 60,
              height: 60,
              fontSize: "1.8rem",
              boxShadow: "0 12px 40px -6px rgba(212,175,55,0.35)",
            }}
          >
            P
          </div>
          <h1 style={{ fontSize: "2.2rem", letterSpacing: "-0.02em" }}>Aurum PMS</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Discretionary Portfolio Management Service
          </p>
          <div
            style={{
              width: 48,
              height: 2,
              background: "linear-gradient(90deg, transparent, var(--gold), transparent)",
              margin: "16px auto 0",
              borderRadius: 2,
            }}
          />
        </div>

        <Card glass>
          {/* ── LOGIN ── */}
          {view === "login" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Sign in</h2>
              <form onSubmit={handleLogin}>
                <Field
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setEmailErr(""); }}
                  onBlur={() => setEmailErr(validateEmail(email))}
                  placeholder="you@example.com"
                  error={emailErr}
                />
                <Field
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
                <div style={{ marginTop: 8 }}>
                  <Button variant="primary" block loading={loading} type="submit">
                    Sign In
                  </Button>
                </div>
              </form>
              <div style={{ marginTop: 16, display: "flex", justifyContent: "space-between", fontSize: ".82rem" }}>
                <button
                  className="btn--link"
                  style={{ background: "none", border: "none", color: "var(--gold-2)", cursor: "pointer", padding: 0, font: "inherit" }}
                  onClick={() => setView("forgot")}
                >
                  Forgot password?
                </button>
                <button
                  className="btn--link"
                  style={{ background: "none", border: "none", color: "var(--gold-2)", cursor: "pointer", padding: 0, font: "inherit" }}
                  onClick={() => setView("register")}
                >
                  Create account
                </button>
              </div>

              {/* ── Demo quick-login ── */}
              <div style={{ marginTop: 20, borderTop: "1px solid var(--border-light)", paddingTop: 16 }}>
                <p className="faint center" style={{ fontSize: ".72rem", marginBottom: 10, letterSpacing: ".04em", textTransform: "uppercase" }}>
                  Quick demo access
                </p>
                <div style={{ display: "flex", gap: 8, flexDirection: "column" }}>
                  {(["compliance", "rm", "investor"] as Array<"compliance" | "rm" | "investor">).map((r) => {
                    const labels: Record<string, string> = {
                      compliance: "✓  Compliance Officer",
                      rm: "❖  Relationship Manager",
                      investor: "◉  Investor — Asha Rao",
                    };
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => handleDemoLogin(r)}
                        disabled={loading}
                        style={{
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius-sm)",
                          background: "var(--bg-secondary)",
                          color: "var(--text)",
                          padding: "8px 12px",
                          cursor: "pointer",
                          font: "inherit",
                          fontSize: ".83rem",
                          fontWeight: 500,
                          transition: "background 0.15s",
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          textAlign: "left" as const,
                        }}
                      >
                        {labels[r]}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* ── REGISTER ── */}
          {view === "register" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Create account</h2>
              <form onSubmit={handleRegister}>
                <Field
                  label="Full Name"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="Your full name"
                />
                <Field
                  label="Email"
                  type="email"
                  value={regEmail}
                  onChange={(e) => { setRegEmail(e.target.value); setRegEmailErr(""); }}
                  onBlur={() => setRegEmailErr(validateEmail(regEmail))}
                  placeholder="you@example.com"
                  error={regEmailErr}
                />
                <div className="field">
                  <label className="label">Phone (optional)</label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <select
                      className="select"
                      value={regCountryCode}
                      onChange={(e) => setRegCountryCode(e.target.value)}
                      style={{ width: 110, flexShrink: 0 }}
                    >
                      {COUNTRY_CODES.map((c) => (
                        <option key={c.code} value={c.code}>{c.flag} {c.label}</option>
                      ))}
                    </select>
                    <input
                      className="input"
                      type="tel"
                      value={regPhone}
                      onChange={(e) => setRegPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
                      placeholder="9876543210"
                      maxLength={10}
                      style={{ flex: 1 }}
                    />
                  </div>
                </div>
                <SelectField label="Role" value={regRole} onChange={(e) => {
                  setRegRole(e.target.value);
                  const needsCode = e.target.value === "rm" || e.target.value === "compliance" || e.target.value === "admin";
                  setShowAccessCode(needsCode);
                  if (!needsCode) setAccessCode("");
                }}>
                  <option value="investor">Investor</option>
                  <option value="rm">Relationship Manager</option>
                  <option value="compliance">Compliance Officer</option>
                  <option value="admin">Admin</option>
                </SelectField>
                {showAccessCode && (
                  <div style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-light)",
                    borderRadius: 8,
                    padding: "12px 14px",
                    marginBottom: 12,
                  }}>
                    <p style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: 8 }}>
                      {regRole === "rm" ? "Relationship Manager" : regRole === "compliance" ? "Compliance Officer" : "Admin"} registration requires an access code.
                      {regRole !== "admin" ? " Contact your administrator if you don't have one." : ""}
                    </p>
                    <Field
                      label="Access Code"
                      type="password"
                      value={accessCode}
                      onChange={(e) => setAccessCode(e.target.value)}
                      placeholder="Enter access code"
                    />
                  </div>
                )}
                <div>
                  <Field
                    label="Password"
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Min 6 characters"
                    error={regPassword && regPassword.length < 6 ? "Password must be at least 6 characters" : ""}
                  />
                  {regPassword && regPassword.length >= 1 && (() => {
                    const s = getPasswordStrength(regPassword);
                    return (
                      <div style={{ marginTop: -8, marginBottom: 12 }}>
                        <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                          {[25, 50, 75, 100].map((threshold) => (
                            <div
                              key={threshold}
                              style={{
                                flex: 1,
                                height: 4,
                                borderRadius: 2,
                                background: s.percent >= threshold ? s.color : "var(--border-light)",
                                transition: "background 0.3s",
                              }}
                            />
                          ))}
                        </div>
                        <span style={{ fontSize: ".75rem", color: s.color, fontWeight: 600 }}>
                          {s.label}
                        </span>
                      </div>
                    );
                  })()}
                </div>
                <Field
                  label="Confirm Password"
                  type="password"
                  value={regConfirm}
                  onChange={(e) => setRegConfirm(e.target.value)}
                  placeholder="Re-enter password"
                />
                <div style={{ marginTop: 8 }}>
                  <Button variant="primary" block loading={loading} type="submit">
                    Create Account
                  </Button>
                </div>
              </form>
              <div className="center" style={{ marginTop: 16, fontSize: ".82rem" }}>
                <button
                  style={{ background: "none", border: "none", color: "var(--gold-2)", cursor: "pointer", padding: 0, font: "inherit" }}
                  onClick={() => setView("login")}
                >
                  Already have an account? Sign in
                </button>
              </div>
            </>
          )}

          {/* ── VERIFY (post-signup) ── */}
          {view === "verify" && (
            <>
              <h2 style={{ marginBottom: 8 }}>Verify your account</h2>
              <p className="muted" style={{ marginBottom: 18, fontSize: ".9rem" }}>
                We sent a verification link to <strong>{regEmail}</strong> — open it to confirm your email.
              </p>
              {regPhone ? (
                <form onSubmit={handleVerifyPhone}>
                  <p className="muted" style={{ marginBottom: 12, fontSize: ".88rem" }}>
                    Enter the 6-digit code we texted to <strong>{regPhone}</strong>.
                  </p>
                  <Field
                    label="SMS code"
                    inputMode="numeric"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    placeholder="123456"
                  />
                  {otpMsg && (
                    <p className="faint" style={{ fontSize: ".8rem", marginBottom: 8 }}>{otpMsg}</p>
                  )}
                  <div style={{ marginTop: 8 }}>
                    <Button variant="primary" block loading={loading} type="submit">
                      Verify Phone
                    </Button>
                  </div>
                  <div style={{ marginTop: 14, display: "flex", gap: 16, justifyContent: "center", fontSize: ".82rem" }}>
                    <button
                      type="button"
                      style={{ background: "none", border: "none", color: "var(--primary)", cursor: "pointer", padding: 0, font: "inherit" }}
                      onClick={handleResendOtp}
                      disabled={loading}
                    >
                      Resend code
                    </button>
                    <button
                      type="button"
                      style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", padding: 0, font: "inherit" }}
                      onClick={() => navigate(homeFor(regRole || "investor"))}
                    >
                      Skip for now
                    </button>
                  </div>
                </form>
              ) : (
                <Button variant="primary" block onClick={() => navigate(homeFor(regRole || "investor"))}>
                  Continue to app
                </Button>
              )}
            </>
          )}

          {/* ── FORGOT PASSWORD ── */}
          {view === "forgot" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Reset password</h2>
              {forgotSent ? (
                <div>
                  <div className="success-check">{"✓"}</div>
                  <p className="center muted" style={{ marginBottom: 16 }}>
                    If an account exists with that email, we&rsquo;ve sent a reset link.
                  </p>
                  <Button variant="ghost" block onClick={() => { setView("login"); setForgotSent(false); }}>
                    Back to sign in
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleForgot}>
                  <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
                    Enter your email and we&rsquo;ll send a password reset link.
                  </p>
                  <Field
                    label="Email"
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="you@example.com"
                  />
                  <div style={{ marginTop: 8 }}>
                    <Button variant="primary" block loading={loading} type="submit">
                      Send Reset Link
                    </Button>
                  </div>
                  <div className="center" style={{ marginTop: 16, fontSize: ".82rem" }}>
                    <button
                      style={{ background: "none", border: "none", color: "var(--gold-2)", cursor: "pointer", padding: 0, font: "inherit" }}
                      onClick={() => setView("login")}
                    >
                      Back to sign in
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

          <p className="faint center" style={{ fontSize: ".74rem", marginTop: 18, marginBottom: 0 }}>
            SEBI-registered PMS &middot; Secure authentication
            <br />
            <a href="/privacy" style={{ color: "var(--gold-2, #b8860b)", textDecoration: "none" }}>Privacy Policy</a>
          </p>
        </Card>
      </div>
    </div>
  );
}
