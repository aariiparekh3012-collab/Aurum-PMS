import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ToastProvider } from "@/components/ui";
import Layout from "@/components/Layout";

// Auth
import { LoginPage } from "@/features/auth/LoginPage";
import { VerifyEmailPage } from "@/features/auth/VerifyEmailPage";

// Features
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import OnboardingWizard from "@/features/onboarding/components/OnboardingWizard";
import { ApplicationsPage } from "@/features/applications/ApplicationsPage";
import { ClientsListPage } from "@/features/clients/ClientsListPage";
import { ClientDetailPage } from "@/features/clients/ClientDetailPage";
import { ComplianceReviewPage } from "@/features/compliance/ComplianceReviewPage";
import { ApplicationReviewDetail } from "@/features/compliance/ApplicationReviewDetail";
import ReviewDashboard from "@/features/compliance/components/ReviewDashboard";
import { HoldingsPage } from "@/features/portfolio/HoldingsPage";
import PortfolioDashboard from "@/features/portfolio/components/PortfolioDashboard";
import { OrderBookPage } from "@/features/trading/OrderBookPage";
import { TradeBlotterPage } from "@/features/trading/TradeBlotterPage";
import { PerformancePage } from "@/features/performance/PerformancePage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { DailyReportsPage } from "@/features/reports/DailyReportsPage";
import { ActivityFeedPage } from "@/features/notifications/ActivityFeedPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { SecuritiesPage } from "@/features/reference/SecuritiesPage";
import { StrategiesPage } from "@/features/reference/StrategiesPage";
import { BrokersPage } from "@/features/reference/BrokersPage";
import { FeeSchedulesPage } from "@/features/reference/FeeSchedulesPage";
import { InvestorPortal } from "@/features/investor/InvestorPortal";
import { MessagesPage } from "@/features/messaging/MessagesPage";
import { NotFoundPage } from "@/features/misc/NotFoundPage";

function ProtectedRoutes() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;

  const isInvestor = user.role === "investor";
  const isStaff = !isInvestor;

  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Dashboard */}
        <Route path="/dashboard" element={<DashboardPage />} />

        {/* Onboarding */}
        <Route path="/onboarding" element={<OnboardingWizard />} />

        {/* Applications */}
        {isStaff && <Route path="/applications" element={<ApplicationsPage />} />}

        {/* Clients */}
        {isStaff && <Route path="/clients" element={<ClientsListPage />} />}
        {isStaff && <Route path="/clients/:id" element={<ClientDetailPage />} />}

        {/* Compliance */}
        {isStaff && <Route path="/compliance" element={<ComplianceReviewPage />} />}
        {isStaff && <Route path="/compliance/review/:applicationId" element={<ApplicationReviewDetail />} />}
        {isStaff && <Route path="/review" element={<ReviewDashboard />} />}

        {/* Portfolio */}
        <Route path="/portfolio" element={isInvestor ? <InvestorPortal /> : <PortfolioDashboard />} />
        {isStaff && <Route path="/holdings" element={<HoldingsPage />} />}
        <Route path="/my-portfolio" element={<InvestorPortal />} />

        {/* Trading */}
        {isStaff && <Route path="/orders" element={<OrderBookPage />} />}
        {isStaff && <Route path="/trades" element={<TradeBlotterPage />} />}

        {/* Performance & Reports */}
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/daily-reports" element={<DailyReportsPage />} />

        {/* Reference data */}
        {isStaff && <Route path="/securities" element={<SecuritiesPage />} />}
        {isStaff && <Route path="/strategies" element={<StrategiesPage />} />}
        {isStaff && <Route path="/brokers" element={<BrokersPage />} />}
        {isStaff && <Route path="/fee-schedules" element={<FeeSchedulesPage />} />}

        {/* Messaging, Notifications & Settings */}
        <Route path="/messages" element={<MessagesPage />} />
        <Route path="/activity" element={<ActivityFeedPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Default redirect */}
        <Route
          path="/"
          element={<Navigate to={isInvestor ? "/my-portfolio" : "/dashboard"} replace />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/*" element={<ProtectedRoutes />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
