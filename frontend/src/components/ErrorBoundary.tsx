import { Component, type ReactNode } from "react";
import { Button } from "./ui";

interface Props { children: ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="auth-wrap">
          <div style={{ textAlign: "center", maxWidth: 480 }}>
            <div
              style={{
                width: 72, height: 72, borderRadius: "50%", margin: "0 auto 20px",
                display: "grid", placeItems: "center", fontSize: "2rem",
                background: "rgba(248,113,113,.12)", color: "var(--danger)",
                border: "1px solid rgba(248,113,113,.3)",
              }}
            >
              !
            </div>
            <h2 style={{ marginBottom: 8 }}>Something went wrong</h2>
            <p className="muted" style={{ marginBottom: 8, lineHeight: 1.6 }}>
              An unexpected error occurred. Please try refreshing the page.
            </p>
            {this.state.error && (
              <pre
                style={{
                  textAlign: "left", fontSize: ".78rem", padding: 16,
                  background: "var(--surface)", borderRadius: 8,
                  border: "1px solid var(--line)", overflow: "auto",
                  maxHeight: 120, marginBottom: 20, color: "var(--muted)",
                }}
              >
                {this.state.error.message}
              </pre>
            )}
            <div className="row" style={{ gap: 12, justifyContent: "center" }}>
              <Button variant="primary" onClick={() => window.location.reload()}>
                Refresh Page
              </Button>
              <Button variant="ghost" onClick={() => { this.setState({ hasError: false, error: null }); }}>
                Try Again
              </Button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
