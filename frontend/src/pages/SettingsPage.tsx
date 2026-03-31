import { FormEvent, useState } from "react";

import { api } from "../api";

export function SettingsPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      const result = await api.updateEmail(email.trim());
      setStatus(`Email updated to ${result.email ?? "unknown"}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update email.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <h2>Studio Settings</h2>
      <form className="grid" onSubmit={handleSubmit}>
        <label className="field">
          Email address
          <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Updating..." : "Update email"}
        </button>
      </form>
      {status ? <p>{status}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
