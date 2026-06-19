import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { DashboardScreen } from "../screens/DashboardScreen";
import { ApplicationsScreen } from "../screens/ApplicationsScreen";
import { ClientsListScreen } from "../screens/ClientsListScreen";
import { ClientDetailScreen } from "../screens/ClientDetailScreen";
import { OnboardingScreen } from "../screens/onboarding/OnboardingScreen";
import { PortfolioScreen } from "../screens/PortfolioScreen";
import { TradingScreen } from "../screens/TradingScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { InvestorPortalScreen } from "../screens/InvestorPortalScreen";
import { PerformanceScreen } from "../screens/PerformanceScreen";
import { ReportsScreen } from "../screens/ReportsScreen";
import { ComplianceReviewScreen } from "../screens/ComplianceReviewScreen";
import { ActivityFeedScreen } from "../screens/ActivityFeedScreen";
import { SettingsScreen } from "../screens/SettingsScreen";
import { SecuritiesScreen } from "../screens/SecuritiesScreen";
import { auth, canSeeTab } from "../lib/auth";
import { colors, font } from "../lib/theme";

const Tab = createBottomTabNavigator();
const ClientsStack = createNativeStackNavigator();

function ClientsStackNav() {
  return (
    <ClientsStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        headerTitleStyle: font.semibold,
      }}
    >
      <ClientsStack.Screen name="ClientsList" component={ClientsListScreen} options={{ headerShown: false }} />
      <ClientsStack.Screen name="ClientDetail" component={ClientDetailScreen} options={{ title: "Client" }} />
    </ClientsStack.Navigator>
  );
}

const TAB_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  DashboardTab: "grid-outline",
  OnboardingTab: "add-circle-outline",
  ApplicationsTab: "documents-outline",
  ComplianceTab: "shield-checkmark-outline",
  ClientsTab: "people-outline",
  SecuritiesTab: "server-outline",
  PortfolioTab: "pie-chart-outline",
  TradingTab: "swap-horizontal-outline",
  InvestorTab: "wallet-outline",
  PerformanceTab: "trending-up-outline",
  ReportsTab: "document-text-outline",
  ActivityTab: "notifications-outline",
  SettingsTab: "settings-outline",
  ProfileTab: "person-circle-outline",
};

interface TabDef {
  name: string;
  title: string;
  component: React.ComponentType<any>;
  renderFn?: (onLogout: () => void) => React.ReactNode;
}

export function AppNavigator({ onLogout }: { onLogout: () => void }) {
  const role = auth.getUser()?.role;

  const allTabs: TabDef[] = [
    { name: "DashboardTab", title: "Home", component: DashboardScreen },
    { name: "OnboardingTab", title: "Onboard", component: OnboardingScreen },
    { name: "ApplicationsTab", title: "Review", component: ApplicationsScreen },
    { name: "ComplianceTab", title: "Comply", component: ComplianceReviewScreen },
    { name: "ClientsTab", title: "Clients", component: ClientsStackNav },
    { name: "SecuritiesTab", title: "Ref Data", component: SecuritiesScreen },
    { name: "PortfolioTab", title: "Portfolio", component: PortfolioScreen },
    { name: "TradingTab", title: "Trading", component: TradingScreen },
    { name: "InvestorTab", title: "My Portfolio", component: InvestorPortalScreen },
    { name: "PerformanceTab", title: "Perf", component: PerformanceScreen },
    { name: "ReportsTab", title: "Reports", component: ReportsScreen },
    { name: "ActivityTab", title: "Activity", component: ActivityFeedScreen },
    { name: "SettingsTab", title: "Settings", component: SettingsScreen },
    { name: "ProfileTab", title: "Profile", component: ProfileScreen, renderFn: (logout) => <ProfileScreen onLogout={logout} /> },
  ];

  const visibleTabs = allTabs.filter((t) => canSeeTab(role, t.name));

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        headerTitleStyle: font.semibold,
        headerShadowVisible: false,
        tabBarStyle: {
          backgroundColor: colors.bgCard,
          borderTopColor: colors.line,
          borderTopWidth: 1,
          height: 88,
          paddingBottom: 28,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.gold,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { ...font.medium, fontSize: 11 },
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={TAB_ICONS[route.name] ?? "ellipse"} size={size} color={color} />
        ),
      })}
    >
      {visibleTabs.map((tab) =>
        tab.renderFn ? (
          <Tab.Screen key={tab.name} name={tab.name} options={{ title: tab.title, headerShown: false }}>
            {() => tab.renderFn!(onLogout)}
          </Tab.Screen>
        ) : (
          <Tab.Screen
            key={tab.name}
            name={tab.name}
            component={tab.component}
            options={{ title: tab.title, headerShown: false }}
          />
        )
      )}
    </Tab.Navigator>
  );
}
