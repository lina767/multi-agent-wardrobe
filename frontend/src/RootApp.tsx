import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthProvider";
import { App as DashboardApp } from "./App";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { PublicHome } from "./pages/PublicHome";

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <p className="authLoading">Loading session...</p>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

function GuestRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <p className="authLoading">Loading session...</p>;
  }
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

function DashboardLayout() {
  const { user, signOut } = useAuth();
  return (
    <>
      <header className="topbar">
        <div>
          <strong>Dashboard</strong>
          <p>{user?.email ?? "Signed in"}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            void signOut();
          }}
        >
          Logout
        </button>
      </header>
      <DashboardApp />
    </>
  );
}

export function RootApp() {
  return (
    <Routes>
      <Route path="/" element={<PublicHome />} />
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage initialMode="login" />} />
        <Route path="/signup" element={<LoginPage initialMode="signup" />} />
      </Route>
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard/*" element={<DashboardLayout />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
