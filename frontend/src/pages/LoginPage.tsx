import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

const MAGIC_LINK_COOLDOWN_SECONDS = 60;

function formatAuthError(message: string, method: "magic_link" | "password"): string {
  const lower = message.toLowerCase();
  if (lower.includes("email rate limit exceeded") || lower.includes("rate limit")) {
    return "Too many email requests right now. Please wait a moment, or sign in with password.";
  }
  if (method === "password" && (lower.includes("invalid login credentials") || lower.includes("invalid credentials"))) {
    return "Invalid email or password. Please try again, or use a magic link.";
  }
  return message;
}

export function LoginPage() {
  const { sendMagicLink, signInWithPassword, requestPasswordReset, authError } = useAuth();
  const [method, setMethod] = useState<"magic_link" | "password">("magic_link");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [magicLinkCooldownUntil, setMagicLinkCooldownUntil] = useState<number | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  useEffect(() => {
    if (!magicLinkCooldownUntil) {
      setCooldownSeconds(0);
      return;
    }

    function updateCountdown() {
      const next = Math.max(0, Math.ceil((magicLinkCooldownUntil - Date.now()) / 1000));
      setCooldownSeconds(next);
    }

    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [magicLinkCooldownUntil]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setStatus(null);
    try {
      if (method === "magic_link") {
        if (magicLinkCooldownUntil && Date.now() < magicLinkCooldownUntil) {
          setError(`Please wait ${Math.max(1, cooldownSeconds)}s before requesting another magic link.`);
          return;
        }
        await sendMagicLink(email.trim());
        setStatus("Magic link sent. Check your inbox to continue.");
        setMagicLinkCooldownUntil(Date.now() + MAGIC_LINK_COOLDOWN_SECONDS * 1000);
      } else {
        await signInWithPassword(email.trim(), password);
        setStatus("Signed in successfully.");
      }
    } catch (requestError) {
      const fallback = "Unable to sign in.";
      const rawMessage = requestError instanceof Error ? requestError.message : fallback;
      setError(formatAuthError(rawMessage, method));
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePasswordReset() {
    if (!email.trim()) {
      setError("Bitte gib zuerst deine E-Mail-Adresse ein.");
      setStatus(null);
      return;
    }
    setSubmitting(true);
    setError(null);
    setStatus(null);
    try {
      await requestPasswordReset(email.trim());
      setStatus("Password reset link sent. Please check your inbox.");
    } catch (requestError) {
      const fallback = "Unable to send password reset.";
      const rawMessage = requestError instanceof Error ? requestError.message : fallback;
      setError(formatAuthError(rawMessage, method));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="layout">
      <section className="card authCard authCardLuxury">
        <p className="eyebrow">Secure Access</p>
        <h1>Welcome back</h1>
        <p>Log in with magic link or password to enter your style studio.</p>
        <div className="row">
          <button
            type="button"
            className={method === "magic_link" ? "linkButton" : "linkButton subtle"}
            onClick={() => {
              setMethod("magic_link");
              setStatus(null);
              setError(null);
            }}
          >
            Magic link
          </button>
          <button
            type="button"
            className={method === "password" ? "linkButton" : "linkButton subtle"}
            onClick={() => {
              setMethod("password");
              setStatus(null);
              setError(null);
            }}
          >
            Password
          </button>
        </div>
        <form className="grid" onSubmit={handleSubmit}>
          <label className="field">
            Email
            <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          {method === "password" ? (
            <label className="field">
              Passwort
              <input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
          ) : null}
          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : method === "magic_link" ? "Send magic link" : "Sign in with password"}
          </button>
          {method === "password" ? (
            <button type="button" className="linkButton subtle" onClick={() => void handlePasswordReset()} disabled={submitting}>
              Forgot password?
            </button>
          ) : null}
        </form>
        {method === "magic_link" && cooldownSeconds > 0 ? (
          <p className="metaNote">
            Magic link cooldown active. Try again in {cooldownSeconds}s or use password login.
          </p>
        ) : null}
        {status ? <p>{status}</p> : null}
        {authError ? <p className="error">{authError}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <p>
          <Link to="/">Back to home</Link>
        </p>
      </section>
    </main>
  );
}
