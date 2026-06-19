import { Outlet, NavLink } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div>
      <nav style={{
        background: "var(--surface)", borderBottom: "1px solid var(--border)",
        padding: "0 24px", display: "flex", alignItems: "center", height: 56, gap: 24,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, marginRight: 32 }}>PMS Platform</span>
        <NavLink to="/portfolio" style={({ isActive }) => ({
          fontSize: 14, fontWeight: 500, textDecoration: "none",
          color: isActive ? "var(--primary)" : "var(--text-secondary)",
        })}>Portfolio</NavLink>
        <NavLink to="/onboarding" style={({ isActive }) => ({
          fontSize: 14, fontWeight: 500, textDecoration: "none",
          color: isActive ? "var(--primary)" : "var(--text-secondary)",
        })}>Onboarding</NavLink>
        {(user?.role === "compliance" || user?.role === "relationship_manager") && (
          <NavLink to="/review" style={({ isActive }) => ({
            fontSize: 14, fontWeight: 500, textDecoration: "none",
            color: isActive ? "var(--primary)" : "var(--text-secondary)",
          })}>Review Queue</NavLink>
        )}
        <NavLink to="/daily-reports" style={({ isActive }) => ({
          fontSize: 14, fontWeight: 500, textDecoration: "none",
          color: isActive ? "var(--primary)" : "var(--text-secondary)",
        })}>Daily Reports</NavLink>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {user?.sub} ({user?.role})
          </span>
          <button className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 13 }} onClick={logout}>
            Sign Out
          </button>
        </div>
      </nav>
      <main style={{ maxWidth: 900, margin: "32px auto", padding: "0 24px" }}>
        <Outlet />
      </main>
    </div>
  );
}
