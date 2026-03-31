import { useState } from "react";

import { api } from "../api";
import type { Suggestion, SuggestionsResponse } from "../types";

export function DailyOutfitPage() {
  const [mood, setMood] = useState("focus");
  const [occasion, setOccasion] = useState("casual");
  const [location, setLocation] = useState("");
  const [response, setResponse] = useState<SuggestionsResponse | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLoad() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSuggestions(mood, occasion, location);
      setResponse(data);
      setSuggestions((data.suggestions ?? []).slice(0, 3));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load suggestions.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>Daily Edit</h2>
      <p>Choose how you want to feel today. We will compose three weather-aware outfit options with clear reasoning.</p>
      {error ? <p className="error">{error}</p> : null}
      <div className="row">
        <label className="field inline">
          Mood
          <select value={mood} onChange={(event) => setMood(event.target.value)}>
            <option value="focus">focus</option>
            <option value="power">power</option>
            <option value="creative">creative</option>
            <option value="comfort">comfort</option>
            <option value="social">social</option>
          </select>
        </label>
        <label className="field inline">
          Occasion
          <select value={occasion} onChange={(event) => setOccasion(event.target.value)}>
            <option value="casual">casual</option>
            <option value="work">work</option>
            <option value="date">date</option>
            <option value="event">event</option>
          </select>
        </label>
        <label className="field inline">
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Berlin,de" />
        </label>
        <button type="button" onClick={() => void handleLoad()} disabled={loading}>
          {loading ? "Generating..." : "Generate top 3"}
        </button>
      </div>
      {response?.context?.weather ? (
        <p>
          Weather: {response.context.weather.temperature_c ?? "-"}°C, rain {Math.round((response.context.weather.rain_probability ?? 0) * 100)}%, UV{" "}
          {response.context.weather.uv_index ?? "-"}, {response.context.weather.forecast_summary ?? "no summary"}
        </p>
      ) : null}
      {suggestions.map((suggestion) => (
        <article key={suggestion.id} className="suggestion">
          <h3>{suggestion.item_names.join(" + ")}</h3>
          <p>Score: {suggestion.total_score.toFixed(3)}</p>
          <p>Editorial note: {suggestion.explanation}</p>
        </article>
      ))}
    </section>
  );
}
