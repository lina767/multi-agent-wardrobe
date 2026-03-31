import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function LoginPage() {
  const { sendMagicLink, authError } = useAuth();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setStatus(null);
    try {
      await sendMagicLink(email.trim());
      setStatus("Magic link sent. Check your inbox to continue.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to send magic link.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="layout">
      <section className="card authCard">
        <h1>Welcome back</h1>
        <p>Enter your email and we will send a secure magic link to your style studio.</p>
        <form className="grid" onSubmit={handleSubmit}>
          <label className="field">
            Email
            <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Sending..." : "Send magic link"}
          </button>
        </form>
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
