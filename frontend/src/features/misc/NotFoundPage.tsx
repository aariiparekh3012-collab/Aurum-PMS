import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui";
import { auth, homeFor } from "../../lib/auth";

export function NotFoundPage() {
  const navigate = useNavigate();
  const role = auth.getUser()?.role;

  return (
    <div className="auth-wrap">
      <div style={{ textAlign: "center", maxWidth: 440, animation: "slideUp .5s ease" }}>
        <div
          style={{
            fontSize: "6rem",
            fontFamily: "'Segoe UI Variable', 'Segoe UI', sans-serif",
            fontWeight: 700,
            color: "var(--primary)",
            lineHeight: 1,
            marginBottom: 8,
          }}
        >
          404
        </div>
        <h2 style={{ marginBottom: 8 }}>Page not found</h2>
        <p className="muted" style={{ marginBottom: 28, lineHeight: 1.6 }}>
          The page you are looking for does not exist or you do not have permission to access it.
        </p>
        <div className="row" style={{ gap: 12, justifyContent: "center" }}>
          <Button variant="primary" onClick={() => navigate(homeFor(role))}>
            Go to Dashboard
          </Button>
          <Button variant="ghost" onClick={() => navigate(-1)}>
            Go Back
          </Button>
        </div>
      </div>
    </div>
  );
}
