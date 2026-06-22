import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { auth } from "@/lib/auth";

/* ── Icon helper ──────────────────────────────────────────────────────── */
function Icon({ d, width = 18, height = 18 }: { d: string; width?: number; height?: number }) {
  return (
    <svg width={width} height={height} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

const icons: Record<string, string> = {
  dashboard:  "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10",
  onboarding: "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4-4v2 M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
  apps:       "M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2 M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2z",
  clients:    "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4-4v2 M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  review:     "M9 11l3 3L22 4 M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
  portfolio:  "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
  holdings:   "M18 20V10 M12 20V4 M6 20v-6",
  orders:     "M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5",
  trades:     "M7 17l9.2-9.2M17 17V7H7",
  perf:       "M22 12h-4l-3 9L9 3l-3 9H2",
  reports:    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
  daily:      "M12 8v4l3 3 M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0z",
  securities: "M2 20h20 M5 20V10h3v10 M10 20V4h3v16 M17 20V8h3v12",
  strategies: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z M4 22v-7",
  brokers:    "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  fees:       "M12 1v22 M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
  activity:   "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0",
  settings:   "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  signout:    "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4 M16 17l5-5-5-5 M21 12H9",
};

/* ── Nav config ──────────────────────────────────────────────────────── */
interface NavItem {
  to: string;
  label: string;
  icon: string;
  staffOnly?: boolean;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    label: "Overview",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
      { to: "/activity", label: "Activity", icon: "activity" },
    ],
  },
  {
    label: "Clients",
    items: [
      { to: "/onboarding", label: "Onboarding", icon: "onboarding" },
      { to: "/applications", label: "Applications", icon: "apps", staffOnly: true },
      { to: "/clients", label: "Clients", icon: "clients", staffOnly: true },
      { to: "/review", label: "Review Queue", icon: "review", staffOnly: true },
    ],
  },
  {
    label: "Portfolio",
    items: [
      { to: "/portfolio", label: "Portfolio", icon: "portfolio" },
      { to: "/holdings", label: "Holdings", icon: "holdings", staffOnly: true },
      { to: "/orders", label: "Order Book", icon: "orders", staffOnly: true },
      { to: "/trades", label: "Trades", icon: "trades", staffOnly: true },
    ],
  },
  {
    label: "Analytics",
    items: [
      { to: "/performance", label: "Performance", icon: "perf" },
      { to: "/reports", label: "Reports", icon: "reports" },
      { to: "/daily-reports", label: "Daily Reports", icon: "daily" },
    ],
  },
  {
    label: "Reference",
    items: [
      { to: "/securities", label: "Securities", icon: "securities", staffOnly: true },
      { to: "/strategies", label: "Strategies", icon: "strategies", staffOnly: true },
      { to: "/brokers", label: "Brokers", icon: "brokers", staffOnly: true },
      { to: "/fee-schedules", label: "Fee Schedules", icon: "fees", staffOnly: true },
    ],
  },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isInvestor = user?.role === "investor";
  const authUser = auth.getUser();

  const visibleSections = sections
    .map((s) => ({
      ...s,
      items: s.items.filter((i) => !i.staffOnly || !isInvestor),
    }))
    .filter((s) => s.items.length > 0);

  if (isInvestor) {
    const portfolioSection = visibleSections.find((s) => s.label === "Portfolio");
    if (portfolioSection) {
      portfolioSection.items = [
        { to: "/my-portfolio", label: "My Portfolio", icon: "portfolio" },
      ];
    }
  }

  const displayName = authUser?.full_name ?? user?.sub ?? "User";
  const initial = displayName[0]?.toUpperCase() ?? "U";
  const roleName = (user?.role ?? "user").replace(/_/g, " ");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/dashboard" className="sidebar__logo">
          <div className="sidebar__logo-mark">A</div>
          <div className="sidebar__logo-text">Aurum <span>PMS</span></div>
        </NavLink>

        <nav className="sidebar__nav">
          {visibleSections.map((section) => (
            <div className="sidebar__section" key={section.label}>
              <div className="sidebar__section-label">{section.label}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    "sidebar__link" + (isActive ? " active" : "")
                  }
                >
                  <span className="sidebar__link-icon">
                    <Icon d={icons[item.icon] ?? icons.dashboard} />
                  </span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__user" onClick={() => navigate("/settings")}>
            <div className="sidebar__user-avatar">{initial}</div>
            <div className="sidebar__user-info">
              <div className="sidebar__user-name">{displayName}</div>
              <div className="sidebar__user-role">{roleName}</div>
            </div>
          </div>
          <button className="sidebar__signout" onClick={logout}>
            <Icon d={icons.signout} width={14} height={14} />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
