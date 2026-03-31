import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
      return;
    }
    navigate("/login", { replace: true });
  }, [isAuthenticated, isLoading, navigate]);

  return (
    <main className="layout">
      <section className="card authCard">
        <h1>Authenticating...</h1>
        <p>We are verifying your magic link.</p>
      </section>
    </main>
  );
}
