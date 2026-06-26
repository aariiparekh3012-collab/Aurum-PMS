import { useAuth } from "@/contexts/AuthContext";
import { RMDashboard } from "./RMDashboard";
import { ComplianceDashboard } from "./ComplianceDashboard";
import { AdminDashboard } from "./AdminDashboard";
import { InvestorPortal } from "../investor/InvestorPortal";

export function DashboardPage() {
  const { user } = useAuth();
  const role = user?.role ?? "investor";

  if (role === "investor") return <InvestorPortal />;
  if (role === "compliance") return <ComplianceDashboard />;
  if (role === "relationship_manager") return <RMDashboard />;

  // Default staff/admin dashboard
  return <AdminDashboard />;
}
