import { FormEvent, useState } from "react";

import { api } from "../api";
import type { OnboardingResponse } from "../types";

export function OnboardingPage() {
  const [form, setForm] = useState({
    name: "",
    age: "",
    life_phase: "",
    figure_analysis: "",
    location: "",
  });
  const [result, setResult] = useState<OnboardingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunning(true);
    setError(null);
    try {
      const data = await api.runOnboarding({
        name: form.name || undefined,
        age: form.age ? Number(form.age) : undefined,
        life_phase: form.life_phase || undefined,
        figure_analysis: form.figure_analysis || undefined,
        location: form.location || undefined,
      });
      setResult(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Onboarding failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Initial Setup</p>
      </div>
      <h2>Style Onboarding</h2>
      <p>Set your baseline once. Mood and occasion stay in Daily Outfit Intelligence because they change day to day.</p>
      {error ? <p className="error">{error}</p> : null}
      <form className="grid" onSubmit={handleSubmit}>
        <label className="field">
          Name
          <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
        </label>
        <label className="field">
          Age
          <input value={form.age} onChange={(event) => setForm((prev) => ({ ...prev, age: event.target.value }))} />
        </label>
        <label className="field">
          Life chapter
          <input value={form.life_phase} onChange={(event) => setForm((prev) => ({ ...prev, life_phase: event.target.value }))} />
        </label>
        <label className="field">
          Silhouette note
          <input
            value={form.figure_analysis}
            onChange={(event) => setForm((prev) => ({ ...prev, figure_analysis: event.target.value }))}
          />
        </label>
        <label className="field">
          Location
          <input value={form.location} onChange={(event) => setForm((prev) => ({ ...prev, location: event.target.value }))} />
        </label>
        <button type="submit" disabled={running}>
          {running ? "Running agents..." : "Run onboarding"}
        </button>
      </form>
      {result ? (
        <div>
          <p className="metaNote">
            Context confidence: {result.temporal_state.confidence.toFixed(2)} · factors:{" "}
            {result.temporal_state.state_factors.join(" | ") || "none"}
          </p>
          {result.suggestions.map((suggestion, index) => (
            <article key={index} className="suggestion">
              <h3>{suggestion.item_names.join(" + ")}</h3>
              <p>{suggestion.explanation}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
