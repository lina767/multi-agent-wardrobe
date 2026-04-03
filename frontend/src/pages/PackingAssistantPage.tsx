import { useState } from "react";

import { api } from "../api";
import type { PackingAssistantResponse } from "../types";

export function PackingAssistantPage() {
  const [durationDays, setDurationDays] = useState(5);
  const [location, setLocation] = useState("");
  const [occasionsRaw, setOccasionsRaw] = useState("meeting, casual, sport");
  const [laundryFrequencyDays, setLaundryFrequencyDays] = useState(3);
  const [maxItems, setMaxItems] = useState(12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PackingAssistantResponse | null>(null);

  async function handleGeneratePlan() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getPackingPlan({
        duration_days: durationDays,
        location: location || undefined,
        planned_occasions: occasionsRaw
          .split(",")
          .map((entry) => entry.trim())
          .filter(Boolean),
        laundry_frequency_days: laundryFrequencyDays,
        max_items: maxItems,
      });
      setPlan(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate packing plan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Travel Capsule</p>
      </div>
      <h2>Packing Assistant</h2>
      <p>Set trip details and generate a minimal capsule wardrobe with high outfit coverage.</p>
      {error ? <p className="error">{error}</p> : null}
      <div className="row">
        <label className="field inline">
          Duration (days)
          <input type="number" min={1} max={30} value={durationDays} onChange={(event) => setDurationDays(Number(event.target.value))} />
        </label>
        <label className="field inline">
          Destination
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Berlin,de" />
        </label>
        <label className="field inline">
          Planned occasions
          <input value={occasionsRaw} onChange={(event) => setOccasionsRaw(event.target.value)} placeholder="meeting, casual, sport" />
        </label>
        <label className="field inline">
          Laundry cadence (days)
          <input
            type="number"
            min={1}
            max={14}
            value={laundryFrequencyDays}
            onChange={(event) => setLaundryFrequencyDays(Number(event.target.value))}
          />
        </label>
        <label className="field inline">
          Max items
          <input type="number" min={4} max={40} value={maxItems} onChange={(event) => setMaxItems(Number(event.target.value))} />
        </label>
        <button type="button" onClick={() => void handleGeneratePlan()} disabled={loading}>
          {loading ? "Generating..." : "Generate capsule plan"}
        </button>
      </div>
      {plan ? (
        <>
          <p className="metaNote">
            Coverage: {Math.round(plan.summary.coverage_ratio * 100)}% · Selected pieces: {plan.summary.selected_item_count}
          </p>
          <p className="metaNote">Pack list: {plan.packing_item_names.join(", ")}</p>
          {plan.outfit_plan.map((entry) => (
            <article key={entry.day} className="suggestion">
              <h3>
                Day {entry.day} · {entry.occasion}
              </h3>
              <p className="metaNote">{entry.item_names.join(" + ")}</p>
              <p className="metaNote">Match quality: {Math.round(entry.score * 100)}%</p>
            </article>
          ))}
        </>
      ) : null}
    </section>
  );
}
