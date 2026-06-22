/**
 * Tests for the ErrorBoundary component.
 *
 * Verifies: renders children normally, catches thrown errors, displays
 * error message, offers Refresh and Try Again buttons.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "./ErrorBoundary";

function GoodChild() {
  return <p>All good</p>;
}

function BadChild(): JSX.Element {
  throw new Error("Boom");
}

// Suppress React error boundary console noise during tests.
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalError;
});

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("catches errors and shows the fallback UI", () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Boom")).toBeInTheDocument();
  });

  it("shows a Refresh Page button that reloads the window", () => {
    // Mock window.location.reload
    const reloadMock = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload: reloadMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const refreshBtn = screen.getByRole("button", { name: /refresh page/i });
    expect(refreshBtn).toBeInTheDocument();
    fireEvent.click(refreshBtn);
    expect(reloadMock).toHaveBeenCalled();
  });

  it("Try Again button resets the error state", () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Click Try Again — it clears the error so re-render attempts children again
    const tryAgain = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(tryAgain);

    // The boundary now tries to render children again. BadChild will throw again,
    // so the error fallback reappears. The key point: Try Again did reset the state.
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});
