import React, { useCallback, useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import * as LocalAuthentication from "expo-local-authentication";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ActivityIndicator, Text, View } from "react-native";
import { auth } from "./src/lib/auth";
import { LoginScreen } from "./src/screens/LoginScreen";
import { AppNavigator } from "./src/navigation/AppNavigator";
import { Button } from "./src/components/ui";
import { colors, font } from "./src/lib/theme";

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

const DarkTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.gold,
    background: colors.bg,
    card: colors.bgCard,
    text: colors.text,
    border: colors.line,
    notification: colors.gold,
  },
};

export default function App() {
  const [ready, setReady] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [bioLocked, setBioLocked] = useState(false); // has session but needs biometric unlock

  useEffect(() => {
    (async () => {
      await auth.init();
      const hasSession = auth.isAuthenticated();

      if (hasSession) {
        // Try biometric unlock if hardware supports it
        const compatible = await LocalAuthentication.hasHardwareAsync();
        const enrolled = compatible && (await LocalAuthentication.isEnrolledAsync());

        if (enrolled) {
          const result = await LocalAuthentication.authenticateAsync({
            promptMessage: "Unlock Aurum PMS",
            fallbackLabel: "Use password",
            disableDeviceFallback: false,
          });
          if (result.success) {
            setLoggedIn(true);
          } else {
            // Biometric failed — show lock screen with retry
            setBioLocked(true);
          }
        } else {
          // No biometric — just log in with existing session
          setLoggedIn(true);
        }
      }

      setReady(true);
    })();
  }, []);

  const retryBiometric = async () => {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: "Unlock Aurum PMS",
      fallbackLabel: "Use password",
      disableDeviceFallback: false,
    });
    if (result.success) {
      setBioLocked(false);
      setLoggedIn(true);
    }
  };

  const signOutFromLock = async () => {
    await auth.clear();
    setBioLocked(false);
    setLoggedIn(false);
  };

  const onLayoutRootView = useCallback(async () => {
    if (ready) await SplashScreen.hideAsync();
  }, [ready]);

  if (!ready) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator size="large" color={colors.gold} />
      </View>
    );
  }

  // Biometric lock screen
  if (bioLocked) {
    return (
      <SafeAreaProvider>
        <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center", padding: 40 }}>
          <StatusBar style="light" />
          <Text style={{ ...font.bold, fontSize: 28, color: colors.gold, marginBottom: 8 }}>Aurum PMS</Text>
          <Text style={{ ...font.regular, fontSize: 14, color: colors.textSecondary, marginBottom: 32, textAlign: "center" }}>
            Authenticate to unlock your session
          </Text>
          <Button variant="primary" onPress={retryBiometric}>Unlock with Biometrics</Button>
          <View style={{ marginTop: 16 }}>
            <Button variant="ghost" onPress={signOutFromLock}>Sign in as different user</Button>
          </View>
        </View>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <NavigationContainer theme={DarkTheme} onReady={onLayoutRootView}>
          <StatusBar style="light" />
          {loggedIn ? (
            <AppNavigator
              onLogout={() => {
                queryClient.clear();
                setLoggedIn(false);
              }}
            />
          ) : (
            <LoginScreen onLogin={() => setLoggedIn(true)} />
          )}
        </NavigationContainer>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
