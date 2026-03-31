import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RootApp } from "./RootApp";

const mockUseAuth = vi.fn();

vi.mock("./auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("./App", () => ({
  App: () => <div>Dashboard Content</div>,
}));

describe("RootApp routing", () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
  });

  it("renders public home on /", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      session: null,
      isLoading: false,
      isAuthenticated: false,
      sendMagicLink: vi.fn(),
      signOut: vi.fn(),
    });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <RootApp />
      </MemoryRouter>,
    );
    expect(screen.getByText("Wardrobe Intelligence")).toBeTruthy();
    expect(screen.getByText(/Login with magic link/)).toBeTruthy();
  });

  it("redirects guests from /dashboard to /login", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      session: null,
      isLoading: false,
      isAuthenticated: false,
      sendMagicLink: vi.fn(),
      signOut: vi.fn(),
    });
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <RootApp />
      </MemoryRouter>,
    );
    expect(screen.getByText("Login")).toBeTruthy();
  });

  it("renders protected dashboard for authenticated user", () => {
    mockUseAuth.mockReturnValue({
      user: { email: "test-user@example.com" },
      session: { access_token: "token" },
      isLoading: false,
      isAuthenticated: true,
      sendMagicLink: vi.fn(),
      signOut: vi.fn(),
    });
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <RootApp />
      </MemoryRouter>,
    );
    expect(screen.getByText("Dashboard Content")).toBeTruthy();
    expect(screen.getByText("test-user@example.com")).toBeTruthy();
  });
});
