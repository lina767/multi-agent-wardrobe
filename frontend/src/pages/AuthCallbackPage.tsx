import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getSupabaseClient } from "../lib/supabase";

function readAuthErrorFromUrl(): string | null {
  const url = new URL(window.location.href);
  const q =
    url.searchParams.get("error_description")?.trim() ||
    url.searchParams.get("error")?.trim();
  if (q) {
    return q;
  }
  if (url.hash?.length > 1) {
    const h = new URLSearchParams(url.hash.slice(1));
    return (
      h.get("error_description")?.trim() ||
      h.get("error")?.trim() ||
      null
    );
  }
  return null;
}

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const urlError = readAuthErrorFromUrl();
    if (urlError) {
      setLocalError(urlError);
      const t = window.setTimeout(() => navigate("/login", { replace: true }), 5000);
      return () => window.clearTimeout(t);
    }

    async function run() {
      try {
        const supabase = getSupabaseClient();
        await supabase.auth.initialize();
        const { data } = await supabase.auth.getSession();
        if (cancelled) {
          return;
        }
        if (data.session) {
          navigate("/dashboard", { replace: true });
          return;
        }
        const params = new URLSearchParams(window.location.search);
        if (params.get("code")) {
          setLocalError(
            "This sign-in link could not be completed. Magic links work most reliably when you open them in the same browser where you requested the link (the mail app’s browser often cannot finish PKCE). Try again here, or sign in with a password instead.",
          );
          window.setTimeout(() => navigate("/login", { replace: true }), 9000);
          return;
        }
        navigate("/login", { replace: true });
      } catch {
        if (!cancelled) {
          navigate("/login", { replace: true });
        }
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return (
    <main className="layout">
      <section className="card authCard">
        <h1>Authenticating...</h1>
        {localError ? <p className="error">{localError}</p> : <p>We are verifying your magic link.</p>}
      </section>
    </main>
  );
}
