import { useState } from "react";

import { api } from "../api";
import { trackEvent } from "../telemetry";
import type { LaundryStatus, Suggestion, SuggestionsResponse, WardrobeAnalyticsResponse, WardrobeItem } from "../types";

const moodLabels: Record<string, string> = {
  focus: "Focused",
  power: "Powerful",
  creative: "Creative",
  comfort: "Comfortable",
  social: "Social",
};

const occasionLabels: Record<string, string> = {
  casual: "Casual",
  work: "Work",
  date: "Date",
  event: "Event",
};

interface DailyOutfitPageProps {
  onGeneratedSuggestion?: () => void;
}

export function DailyOutfitPage({ onGeneratedSuggestion }: DailyOutfitPageProps) {
  const [mood, setMood] = useState("focus");
  const [occasion, setOccasion] = useState("casual");
  const [location, setLocation] = useState("");
  const [response, setResponse] = useState<SuggestionsResponse | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [itemsById, setItemsById] = useState<Record<number, WardrobeItem>>({});
  const [wardrobeAnalytics, setWardrobeAnalytics] = useState<WardrobeAnalyticsResponse | null>(null);
  const [feedbackBySuggestion, setFeedbackBySuggestion] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackBusyId, setFeedbackBusyId] = useState<number | null>(null);
  const [logBusyId, setLogBusyId] = useState<number | null>(null);
  const [statusBusyId, setStatusBusyId] = useState<number | null>(null);

  async function handleLoad() {
    setLoading(true);
    setError(null);
    try {
      const [data, analytics] = await Promise.all([api.getSuggestions(mood, occasion, location), api.getWardrobeAnalytics()]);
      const wardrobeItems = await api.listItems();
      setResponse(data);
      setWardrobeAnalytics(analytics);
      setItemsById(Object.fromEntries(wardrobeItems.map((item) => [item.id, item])));
      const nextSuggestions = (data.suggestions ?? []).slice(0, 3);
      setSuggestions(nextSuggestions);
      if (nextSuggestions.length > 0) {
        onGeneratedSuggestion?.();
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load suggestions.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSuggestionFeedback(suggestionId: number, payload: { accepted?: boolean; rating?: number }) {
    setFeedbackBusyId(suggestionId);
    setError(null);
    try {
      await api.sendSuggestionFeedback(suggestionId, { ...payload, occasion });
      trackEvent("suggestion_feedback_submitted", {
        suggestion_id: suggestionId,
        accepted: payload.accepted,
        rating: payload.rating,
        occasion,
      });
      const message = payload.accepted === true ? "Saved as accepted." : payload.accepted === false ? "Saved as skipped." : "Rating saved.";
      setFeedbackBySuggestion((prev) => ({ ...prev, [suggestionId]: message }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save feedback.");
    } finally {
      setFeedbackBusyId(null);
    }
  }

  async function handleLogWorn(suggestion: Suggestion) {
    setLogBusyId(suggestion.id);
    setError(null);
    try {
      await api.logOutfit({
        item_ids: suggestion.items,
        mood,
        occasion,
        style_goals: [mood],
      });
      trackEvent("outfit_logged", {
        suggestion_id: suggestion.id,
        item_count: suggestion.items.length,
        mood,
        occasion,
      });
      setFeedbackBySuggestion((prev) => ({ ...prev, [suggestion.id]: "Outfit logged as worn." }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to log outfit.");
    } finally {
      setLogBusyId(null);
    }
  }

  async function handleSuggestionStatus(suggestion: Suggestion, status: LaundryStatus) {
    setStatusBusyId(suggestion.id);
    setError(null);
    try {
      await Promise.all(
        suggestion.items.map((itemId) =>
          api.updateItem(itemId, {
            status,
            is_available: status === "clean",
          }),
        ),
      );
      const refreshed = await api.listItems();
      setItemsById(Object.fromEntries(refreshed.map((item) => [item.id, item])));
      await handleLoad();
      setFeedbackBySuggestion((prev) => ({
        ...prev,
        [suggestion.id]: status === "clean" ? "Suggestion items marked clean." : `Suggestion items marked ${status}.`,
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update laundry status.");
    } finally {
      setStatusBusyId(null);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Daily Intelligence</p>
      </div>
      <h2>Daily Edit</h2>
      <p>Choose how you want to feel today. We compose three weather-aware options and explain why each one fits your context.</p>
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
        <p className="metaNote weatherPill">
          Weather: {response.context.weather.temperature_c ?? "-"}°C · {response.context.weather.condition ?? "unknown"} · rain{" "}
          {Math.round((response.context.weather.rain_probability ?? 0) * 100)}% · UV {response.context.weather.uv_index ?? "-"} ·{" "}
          {response.context.weather.forecast_summary ?? response.context.weather.condition_raw ?? "no summary"}
        </p>
      ) : null}
      {response?.scientific_note ? <p className="metaNote">{response.scientific_note}</p> : null}
      {wardrobeAnalytics?.gap_analysis?.[0] ? (
        <p className="metaNote">
          Closet opportunity: {wardrobeAnalytics.gap_analysis[0].suggestion} (potential +{wardrobeAnalytics.gap_analysis[0].estimated_new_outfits} outfits)
        </p>
      ) : null}
      {response?.style_profile?.temporal_state?.state_factors?.length ? (
        <p className="metaNote">Style signals: {response.style_profile.temporal_state.state_factors.join(", ")}</p>
      ) : null}
      {loading ? <p className="metaNote">Generating three recommendations...</p> : null}
      {!loading && suggestions.length === 0 && !error ? (
        <div className="emptyState">
          <h3>No suggestions yet</h3>
          <p>Select mood and occasion, then click "Generate top 3" to create your daily edit.</p>
        </div>
      ) : null}
      {suggestions.map((suggestion) => (
        <article key={suggestion.id} className="suggestion">
          <h3>{suggestion.item_names.join(" + ")}</h3>
          <p className="metaNote">
            Match quality: {Math.round(suggestion.total_score * 100)}% · {moodLabels[mood] ?? mood} mood · {occasionLabels[occasion] ?? occasion}
          </p>
          <div className="scoreGrid">
            <p>Color: {Math.round((suggestion.reasoning_breakdown?.color_score ?? 0) * 100)}%</p>
            <p>Style: {Math.round((suggestion.reasoning_breakdown?.style_score ?? 0) * 100)}%</p>
            <p>Context: {Math.round((suggestion.reasoning_breakdown?.context_score ?? 0) * 100)}%</p>
            <p>Sustainability: {Math.round((suggestion.reasoning_breakdown?.sustainability ?? 0) * 100)}%</p>
          </div>
          <p>Editorial note: {suggestion.explanation}</p>
          {suggestion.evidence_tags?.length ? (
            <p className="metaNote">Evidence: {suggestion.evidence_tags.map((tag) => tag.citation_short).join(" • ")}</p>
          ) : null}
          <p className="metaNote">
            Laundry state:{" "}
            {suggestion.items
              .map((itemId) => `${itemsById[itemId]?.name ?? `#${itemId}`} (${itemsById[itemId]?.status ?? "unknown"})`)
              .join(" · ")}
          </p>
          <div className="suggestionActions">
            <button
              type="button"
              onClick={() => void handleSuggestionFeedback(suggestion.id, { accepted: true, rating: 5 })}
              disabled={feedbackBusyId === suggestion.id}
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => void handleSuggestionFeedback(suggestion.id, { accepted: false, rating: 2 })}
              disabled={feedbackBusyId === suggestion.id}
            >
              Skip
            </button>
            <button
              type="button"
              onClick={() => void handleSuggestionFeedback(suggestion.id, { rating: 4 })}
              disabled={feedbackBusyId === suggestion.id}
            >
              Rate 4/5
            </button>
            <button type="button" onClick={() => void handleLogWorn(suggestion)} disabled={logBusyId === suggestion.id}>
              {logBusyId === suggestion.id ? "Logging..." : "Log as worn"}
            </button>
            <button type="button" onClick={() => void handleSuggestionStatus(suggestion, "dirty")} disabled={statusBusyId === suggestion.id}>
              Mark dirty
            </button>
            <button
              type="button"
              onClick={() => void handleSuggestionStatus(suggestion, "dry_cleaning")}
              disabled={statusBusyId === suggestion.id}
            >
              Send to dry cleaning
            </button>
            <button type="button" onClick={() => void handleSuggestionStatus(suggestion, "clean")} disabled={statusBusyId === suggestion.id}>
              Mark clean
            </button>
          </div>
          {feedbackBySuggestion[suggestion.id] ? <p className="metaNote">{feedbackBySuggestion[suggestion.id]}</p> : null}
        </article>
      ))}
    </section>
  );
}
