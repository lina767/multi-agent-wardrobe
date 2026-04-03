import { useMemo, useState } from "react";

import { api } from "../api";
import type {
  LaundryStatus,
  ProactiveSuggestionsResponse,
  Suggestion,
  SuggestionsResponse,
  WardrobeAnalyticsResponse,
  WardrobeItem,
} from "../types";

const moodLabels: Record<string, string> = {
  focus: "Focused",
  power: "Powerful",
  creative: "Creative",
  comfort: "Comfortable",
  social: "Social",
};

const occasionLabels: Record<string, string> = {
  casual: "Casual",
  "smart casual": "Smart Casual",
  event: "Event",
  sport: "Sport",
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
  const [reasonBySuggestion, setReasonBySuggestion] = useState<Record<number, string>>({});
  const [proactive, setProactive] = useState<ProactiveSuggestionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [quickLoading, setQuickLoading] = useState(false);
  const [proactiveLoading, setProactiveLoading] = useState(false);
  const [feedbackBusyId, setFeedbackBusyId] = useState<number | null>(null);
  const [logBusyId, setLogBusyId] = useState<number | null>(null);
  const [statusBusyId, setStatusBusyId] = useState<number | null>(null);
  const scientificNote = response?.scientific_note;
  const showScientificNote = Boolean(scientificNote && !scientificNote.toLowerCase().includes("silhouette"));
  const visibleStateFactors = (response?.style_profile?.temporal_state?.state_factors ?? []).filter(
    (factor) => !factor.toLowerCase().includes("silhouette"),
  );
  const topGap = wardrobeAnalytics?.gap_analysis?.[0];

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

  async function handleQuickFlow() {
    setQuickLoading(true);
    setError(null);
    try {
      const [quickData, analytics, wardrobeItems] = await Promise.all([
        api.getQuickSuggestions(occasion, location, mood),
        api.getWardrobeAnalytics(),
        api.listItems(),
      ]);
      const mappedSuggestions: Suggestion[] = quickData.suggestions.map((entry, index) => ({
        id: -(index + 1),
        items: entry.item_ids,
        item_names: entry.item_names,
        total_score: entry.total_score,
        explanation: entry.explanation,
      }));
      setSuggestions(mappedSuggestions);
      setWardrobeAnalytics(analytics);
      setItemsById(Object.fromEntries(wardrobeItems.map((item) => [item.id, item])));
      setResponse({
        context: {
          mood: quickData.context?.mood,
          occasion: quickData.context?.occasion,
          weather: quickData.context?.weather,
        },
        suggestions: mappedSuggestions,
        scientific_note: quickData.scientific_note,
      });
      if (mappedSuggestions.length > 0) {
        onGeneratedSuggestion?.();
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate quick suggestions.");
    } finally {
      setQuickLoading(false);
    }
  }

  async function handleLoadProactive() {
    setProactiveLoading(true);
    setError(null);
    try {
      const data = await api.getProactiveSuggestions();
      setProactive(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load proactive suggestions.");
    } finally {
      setProactiveLoading(false);
    }
  }

  async function handleSuggestionFeedback(suggestionId: number, payload: { accepted?: boolean; rating?: number; thumb?: "up" | "down" }) {
    setFeedbackBusyId(suggestionId);
    setError(null);
    try {
      await api.sendSuggestionFeedback(suggestionId, {
        ...payload,
        occasion,
        reason_tags: reasonBySuggestion[suggestionId] ? [reasonBySuggestion[suggestionId]] : [],
        context: {
          mood,
          occasion,
          weather: response?.context?.weather?.condition,
        },
      });
      const message =
        payload.thumb === "up"
          ? "Thumbs up saved. We will prioritize similar combinations."
          : payload.thumb === "down"
            ? "Thumbs down saved. We will avoid similar combinations."
            : payload.accepted === true
              ? "Saved as accepted."
              : payload.accepted === false
                ? "Saved as skipped."
                : "Rating saved.";
      setFeedbackBySuggestion((prev) => ({ ...prev, [suggestionId]: message }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save feedback.");
    } finally {
      setFeedbackBusyId(null);
    }
  }

  const primaryActionLabel = useMemo(() => {
    if (quickLoading) {
      return "Generating quick looks...";
    }
    return "Dress me (quick)";
  }, [quickLoading]);

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
      <h2>Dress Me</h2>
      <p>Quick flow: choose occasion, auto-apply weather, and get 2-3 ready-to-wear outfits in seconds.</p>
      {error ? <p className="error">{error}</p> : null}
      <div className="row">
        <label className="field inline">
          Occasion
          <select value={occasion} onChange={(event) => setOccasion(event.target.value)}>
            <option value="casual">casual</option>
            <option value="smart casual">smart casual</option>
            <option value="event">event</option>
            <option value="sport">sport</option>
          </select>
        </label>
        <label className="field inline">
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Berlin,de" />
        </label>
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
        <button type="button" onClick={() => void handleLoad()} disabled={loading}>
          {loading ? "Generating..." : "Generate top 3"}
        </button>
        <button type="button" onClick={() => void handleQuickFlow()} disabled={quickLoading}>
          {primaryActionLabel}
        </button>
        <button type="button" onClick={() => void handleLoadProactive()} disabled={proactiveLoading}>
          {proactiveLoading ? "Loading calendar..." : "Load proactive suggestions"}
        </button>
      </div>
      {response?.context?.weather ? (
        <p className="metaNote weatherPill">
          Weather: {response.context.weather.temperature_c ?? "-"}°C · {response.context.weather.condition ?? "unknown"} · rain{" "}
          {Math.round((response.context.weather.rain_probability ?? 0) * 100)}% · UV {response.context.weather.uv_index ?? "-"} ·{" "}
          {response.context.weather.forecast_summary ?? response.context.weather.condition_raw ?? "no summary"}
        </p>
      ) : null}
      {showScientificNote ? <p className="metaNote">{scientificNote}</p> : null}
      {topGap ? (
        <div className="metaNote" role="region" aria-label="Gap Analysis">
          <strong>Gap analysis:</strong> {topGap.suggestion}
          <br />
          Impact: +{topGap.estimated_new_outfits} outfits
          {typeof topGap.upgrade_count === "number" ? ` · ${topGap.upgrade_count} items upgraded` : ""}
          {topGap.target_item_archetype ? ` · archetype ${topGap.target_item_archetype}` : ""}
          {typeof topGap.confidence === "number" ? ` · confidence ${Math.round(topGap.confidence * 100)}%` : ""}
          <br />
          Why: {topGap.reason}
        </div>
      ) : null}
      {visibleStateFactors.length ? (
        <p className="metaNote">Style signals: {visibleStateFactors.join(", ")}</p>
      ) : null}
      {loading || quickLoading ? <p className="metaNote">Generating three recommendations...</p> : null}
      {!loading && !quickLoading && suggestions.length === 0 && !error ? (
        <div className="emptyState">
          <h3>No suggestions yet</h3>
          <p>Select mood and occasion, then click "Generate top 3" to create your daily edit.</p>
        </div>
      ) : null}
      {proactive?.entries?.length ? (
        <div className="emptyState">
          <h3>Upcoming calendar suggestions</h3>
          {proactive.entries.map((entry, index) => (
            <p key={`${entry.event.starts_at}-${index}`} className="metaNote">
              {new Date(entry.event.starts_at).toLocaleString()} · {entry.event.title}:{" "}
              {(entry.suggestions[0]?.item_names ?? []).join(" + ") || "No suggestion"}.
            </p>
          ))}
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
            <button type="button" onClick={() => void handleSuggestionFeedback(suggestion.id, { thumb: "up", rating: 5 })} disabled={feedbackBusyId === suggestion.id}>
              Thumb up
            </button>
            <button type="button" onClick={() => void handleSuggestionFeedback(suggestion.id, { thumb: "down", rating: 1 })} disabled={feedbackBusyId === suggestion.id}>
              Thumb down
            </button>
            <label className="field inline">
              Feedback reason
              <select
                value={reasonBySuggestion[suggestion.id] ?? ""}
                onChange={(event) => setReasonBySuggestion((prev) => ({ ...prev, [suggestion.id]: event.target.value }))}
              >
                <option value="">optional</option>
                <option value="fit">fit issue</option>
                <option value="weather">weather mismatch</option>
                <option value="formality">wrong formality</option>
                <option value="style">style mismatch</option>
              </select>
            </label>
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
