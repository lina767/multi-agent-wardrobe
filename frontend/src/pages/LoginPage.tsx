import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

const MAGIC_LINK_COOLDOWN_SECONDS = 60;

type AuthMethod = "magic_link" | "password";
type AuthMode = "login" | "signup";

function formatAuthError(message: string, method: AuthMethod): string {
  const lower = message.toLowerCase();
  if (lower.includes("email rate limit exceeded") || lower.includes("rate limit")) {
    return "Your auth provider rate-limited email delivery. Please wait a moment and try again, or continue with password.";
  }
  if (method === "password" && (lower.includes("invalid login credentials") || lower.includes("invalid credentials"))) {
    return "Invalid email or password. Please try again, or use a magic link.";
  }
  return message;
}

interface LoginPageProps {
  initialMode?: AuthMode;
}

export function LoginPage({ initialMode = "login" }: LoginPageProps) {
  const { sendMagicLink, signInWithPassword, signUpWithPassword, requestPasswordReset, authError } = useAuth();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [method, setMethod] = useState<AuthMethod>("magic_link");
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
        setStatus(
          mode === "signup"
            ? "Sign-up link sent. Check your inbox to confirm your account."
            : "Magic link sent. Check your inbox to continue.",
        );
        setMagicLinkCooldownUntil(Date.now() + MAGIC_LINK_COOLDOWN_SECONDS * 1000);
      } else {
        if (mode === "signup") {
          await signUpWithPassword(email.trim(), password);
          setStatus("Account created. Please check your inbox to verify your email.");
        } else {
          await signInWithPassword(email.trim(), password);
          setStatus("Signed in successfully.");
        }
      }
    } catch (requestError) {
      const fallback = mode === "signup" ? "Unable to sign up." : "Unable to sign in.";
      const rawMessage = requestError instanceof Error ? requestError.message : fallback;
      setError(formatAuthError(rawMessage, method));
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePasswordReset() {
    if (!email.trim()) {
      setError("Please enter your email address first.");
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
        <h1>{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
        <p>
          {mode === "signup"
            ? "Sign up with magic link or password. You can switch to login any time."
            : "Log in with magic link or password to enter your style studio."}
        </p>
        <div className="row">
          <button
            type="button"
            className={mode === "login" ? "linkButton" : "linkButton subtle"}
            onClick={() => {
              setMode("login");
              setStatus(null);
              setError(null);
            }}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === "signup" ? "linkButton" : "linkButton subtle"}
            onClick={() => {
              setMode("signup");
              setStatus(null);
              setError(null);
            }}
          >
            Sign up
          </button>
        </div>
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
              Password
              <input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
          ) : null}
          <button type="submit" disabled={submitting}>
            {submitting
              ? mode === "signup"
                ? "Creating account..."
                : "Signing in..."
              : method === "magic_link"
                ? mode === "signup"
                  ? "Send sign-up link"
                  : "Send magic link"
                : mode === "signup"
                  ? "Create account with password"
                  : "Sign in with password"}
          </button>
          {method === "password" && mode === "login" ? (
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
          <Link to="/">Back to home</Link> ·{" "}
          {mode === "signup" ? (
            <Link to="/login" onClick={() => setMode("login")}>
              Already have an account?
            </Link>
          ) : (
            <Link to="/signup" onClick={() => setMode("signup")}>
              New here? Sign up
            </Link>
          )}
        </p>
      </section>
    </main>
  );
}
