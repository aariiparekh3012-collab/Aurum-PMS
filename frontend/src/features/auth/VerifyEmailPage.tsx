import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "./api";
import { Button, Card } from "../../components/ui";

/** Landing page for the email-verification link (/verify-email?token=...). */
export function VerifyEmailPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<"verifying" | "ok" | "error">("verifying");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage("This link is missing its verification token.");
      return;
    }
    // Small delay so the user sees the loading state
    const timer = setTimeout(() => {
      authApi
        .verifyEmail(token)
        .then((r) => {
          setStatus("ok");
          setMessage(r.message || "Your email has been verified.");
        })
        .catch((e: Error) => {
          setStatus("error");
          setMessage(e.message);
        });
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <Card>
          <div className="center" style={{ flexDirection: "column", textAlign: "center", gap: 4 }}>
            {status === "verifying" && (
              <>
                <div className="spinner" style={{ width: 36, height: 36, border: "3px solid var(--border-light)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 0.8s linear infinite", marginBottom: 12 }} />
                <h2 style={{ marginBottom: 8 }}>Verifying your email</h2>
                <p className="muted">Please wait a moment&hellip;</p>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </>
            )}
            {status === "ok" && (
              <>
                <div className="success-check">✓</div>
                <h2 style={{ marginBottom: 8 }}>Email verified</h2>
                <p className="muted" style={{ marginBottom: 16 }}>{message}</p>
              </>
            )}
            {status === "error" && (
              <>
                <h2 style={{ marginBottom: 8 }}>Verification failed</h2>
                <p className="muted" style={{ marginBottom: 16 }}>{message}</p>
              </>
            )}
            <Button variant="primary" onClick={() => navigate("/login")}>
              Go to sign in
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
