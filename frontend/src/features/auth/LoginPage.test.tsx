/**
 * Tests for the LoginPage component.
 *
 * Validates: login form renders, view switching (login ↔ register ↔ forgot),
 * form submission calls the API, error display, demo login buttons visible.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../../contexts/AuthContext";

// Mock the auth API module
vi.mock("./api", () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn(),
    forgotPassword: vi.fn(),
    sendPhoneOtp: vi.fn(),
    verifyPhone: vi.fn(),
  },
}));

// Mock the toast so we can assert error messages
const mockToast = { error: vi.fn(), success: vi.fn() };
vi.mock("../../components/ui", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("../../components/ui");
  return {
    ...actual,
    useToast: () => mockToast,
  };
});

import { authApi } from "./api";
import { LoginPage } from "./LoginPage";

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("LoginPage", () => {
  it("renders the sign-in form by default", () => {
    renderLoginPage();
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows demo quick-access buttons", () => {
    renderLoginPage();
    expect(screen.getByText(/compliance officer/i)).toBeInTheDocument();
    expect(screen.getByText(/relationship manager/i)).toBeInTheDocument();
    expect(screen.getByText(/investor/i)).toBeInTheDocument();
  });

  it("switches to Create Account view", async () => {
    renderLoginPage();
    fireEvent.click(screen.getByText(/create account/i));
    expect(screen.getByText("Create account")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Your full name")).toBeInTheDocument();
  });

  it("switches to Forgot Password view", async () => {
    renderLoginPage();
    fireEvent.click(screen.getByText(/forgot password/i));
    expect(screen.getByText("Reset password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
  });

  it("can navigate back from forgot to login", () => {
    renderLoginPage();
    fireEvent.click(screen.getByText(/forgot password/i));
    fireEvent.click(screen.getByText(/back to sign in/i));
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  it("shows toast on login error", async () => {
    const loginMock = vi.mocked(authApi.login);
    loginMock.mockRejectedValueOnce(new Error("Invalid email or password"));

    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText("you@example.com"), "bad@example.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Invalid email or password");
    });
  });

  it("calls authApi.login on successful submission", async () => {
    const loginMock = vi.mocked(authApi.login);
    const meMock = vi.mocked(authApi.me);

    loginMock.mockResolvedValueOnce({
      access_token: "tok",
      refresh_token: "ref",
      token_type: "bearer",
      expires_in: 1800,
    });
    meMock.mockResolvedValueOnce({
      id: "abc",
      email: "test@example.com",
      full_name: "Test User",
      role: "investor",
      is_active: true,
      email_verified: true,
      created_at: "2026-01-01",
      last_login_at: null,
    });

    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText("you@example.com"), "test@example.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "StrongPass1");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "StrongPass1",
      });
    });
  });

  it("register form rejects mismatched passwords", async () => {
    renderLoginPage();
    fireEvent.click(screen.getByText(/create account/i));

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Your full name"), "Asha");
    await user.type(screen.getByPlaceholderText("you@example.com"), "asha@example.com");
    await user.type(screen.getByPlaceholderText("Min 8 characters"), "password1");
    await user.type(screen.getByPlaceholderText("Re-enter password"), "password2");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Passwords do not match");
    });
  });
});
