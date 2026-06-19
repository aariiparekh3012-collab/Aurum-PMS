/**
 * Tests for the auth store and role-based access helpers.
 * Run with: npm test
 */
import { beforeEach, describe, expect, it } from "vitest";
import { auth, canAccess, homeFor, ROLE_HOME, type AuthUser } from "./auth";

const user: AuthUser = { subject: "test@example.com", role: "rm" };

beforeEach(() => {
  localStorage.clear();
});

describe("auth store", () => {
  it("starts unauthenticated", () => {
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.getToken()).toBeNull();
    expect(auth.getUser()).toBeNull();
  });

  it("stores tokens and user via setTokens", () => {
    auth.setTokens("access-1", "refresh-1", 900, user);
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.getToken()).toBe("access-1");
    expect(auth.getRefreshToken()).toBe("refresh-1");
    expect(auth.getUser()).toEqual(user);
    expect(auth.hasRefreshToken()).toBe(true);
  });

  it("setSession (dev token) clears any refresh token", () => {
    auth.setTokens("access-1", "refresh-1", 900, user);
    auth.setSession("dev-token", user);
    expect(auth.getToken()).toBe("dev-token");
    expect(auth.getRefreshToken()).toBeNull();
    expect(auth.hasRefreshToken()).toBe(false);
  });

  it("reports token expiry within the 60s grace window", () => {
    auth.setTokens("access-1", "refresh-1", 30, user); // expires in 30s < 60s window
    expect(auth.isTokenExpired()).toBe(true);
    auth.setTokens("access-2", "refresh-2", 3600, user);
    expect(auth.isTokenExpired()).toBe(false);
  });

  it("does not treat dev sessions (no expiry) as expired", () => {
    auth.setSession("dev-token", user);
    expect(auth.isTokenExpired()).toBe(false);
  });

  it("updateUser merges partial fields", () => {
    auth.setTokens("a", "r", 900, user);
    auth.updateUser({ full_name: "Test User" });
    expect(auth.getUser()).toEqual({ ...user, full_name: "Test User" });
  });

  it("clear removes everything", () => {
    auth.setTokens("a", "r", 900, user);
    auth.clear();
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.getRefreshToken()).toBeNull();
    expect(auth.getUser()).toBeNull();
  });
});

describe("role-based access", () => {
  it("homeFor returns role home or fallback", () => {
    expect(homeFor("compliance")).toBe(ROLE_HOME.compliance);
    expect(homeFor("rm")).toBe("/applications");
    expect(homeFor("investor")).toBe("/my-portfolio");
    expect(homeFor(undefined)).toBe("/");
    expect(homeFor("unknown")).toBe("/");
  });

  it("compliance can access compliance review pages", () => {
    expect(canAccess("compliance", "/compliance/review")).toBe(true);
    expect(canAccess("compliance", "/compliance/review/abc-123")).toBe(true);
    expect(canAccess("compliance", "/clients/42")).toBe(true);
  });

  it("rm cannot access compliance or investor portal", () => {
    expect(canAccess("rm", "/compliance/review")).toBe(false);
    expect(canAccess("rm", "/my-portfolio")).toBe(false);
    expect(canAccess("rm", "/applications")).toBe(true);
  });

  it("investor is restricted to investor routes", () => {
    expect(canAccess("investor", "/my-portfolio")).toBe(true);
    expect(canAccess("investor", "/onboarding")).toBe(true);
    expect(canAccess("investor", "/clients")).toBe(false);
    expect(canAccess("investor", "/orders")).toBe(false);
    expect(canAccess("investor", "/")).toBe(false);
  });

  it("denies unknown/undefined roles everywhere", () => {
    expect(canAccess(undefined, "/clients")).toBe(false);
    expect(canAccess("hacker", "/clients")).toBe(false);
  });

  it("root path does not leak access via prefix matching", () => {
    // "/" must only match exactly "/", not every path
    expect(canAccess("investor", "/")).toBe(false);
    expect(canAccess("compliance", "/")).toBe(true);
  });
});
