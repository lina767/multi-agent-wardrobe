import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type {
  ColorFamily,
  DresscodeLevel,
  ProfileCheckinCreate,
  Suggestion,
  TemporalState,
  WardrobeCategory,
  WardrobeItem,
  WardrobeItemCreate,
} from "./types";

const categories: WardrobeCategory[] = ["top", "bottom", "outer", "shoes", "accessory"];
const dresscodes: DresscodeLevel[] = ["casual", "smart_casual", "business", "formal"];
const colors: ColorFamily[] = ["neutral", "warm", "cool", "bold", "earth", "pastel"];

const initialForm: WardrobeItemCreate = {
  name: "",
  category: "top",
  color_families: ["neutral"],
  formality: "casual",
  season_tags: [],
  is_available: true,
  style_tags: [],
  quantity: 1,
};

const initialBulkDefaults = {
  category: "top" as WardrobeCategory,
  formality: "casual" as DresscodeLevel,
  color_family: "neutral" as ColorFamily,
};

function splitTags(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

export function App() {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [busyItemIds, setBusyItemIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<WardrobeItemCreate>(initialForm);
  const [seasonTagsText, setSeasonTagsText] = useState("");
  const [styleTagsText, setStyleTagsText] = useState("");
  const [mood, setMood] = useState("focus");
  const [occasion, setOccasion] = useState("casual");
  const [location, setLocation] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [colorAnalysis, setColorAnalysis] = useState<string | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [bulkDefaults, setBulkDefaults] = useState(initialBulkDefaults);
  const [uploadingBulk, setUploadingBulk] = useState(false);
  const [bulkAnalysis, setBulkAnalysis] = useState<string | null>(null);
  const [temporalState, setTemporalState] = useState<TemporalState | null>(null);
  const [checkin, setCheckin] = useState<ProfileCheckinCreate>({
    life_phase: "",
    role_transition: "",
    body_change_note: "",
    fit_confidence: 0.6,
    style_goals: [],
  });
  const [styleGoalsText, setStyleGoalsText] = useState("");
  const [submittingCheckin, setSubmittingCheckin] = useState(false);

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => a.id - b.id),
    [items],
  );

  async function refreshItems() {
    setLoadingItems(true);
    setError(null);
    try {
      setItems(await api.listItems());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load wardrobe.");
    } finally {
      setLoadingItems(false);
    }
  }

  useEffect(() => {
    void refreshItems();
    void refreshTemporalState();
  }, []);

  async function refreshTemporalState() {
    try {
      const state = await api.getProfileState();
      if (state && typeof state === "object" && "features" in state && "dynamic_weights" in state) {
        setTemporalState(state);
      } else {
        setTemporalState(null);
      }
    } catch {
      // Keep the page usable when temporal state is not available yet.
    }
  }

  async function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.createItem({
        ...form,
        season_tags: splitTags(seasonTagsText),
        style_tags: splitTags(styleTagsText),
      });
      setForm(initialForm);
      setSeasonTagsText("");
      setStyleTagsText("");
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create item.");
    }
  }

  async function handleDelete(itemId: number) {
    setBusyItemIds((prev) => new Set(prev).add(itemId));
    setError(null);
    try {
      await api.deleteItem(itemId);
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete item.");
    } finally {
      setBusyItemIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  async function handleUpload(itemId: number, file: File | null) {
    if (!file) {
      return;
    }
    setBusyItemIds((prev) => new Set(prev).add(itemId));
    setError(null);
    try {
      await api.uploadImage(itemId, file);
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Image upload failed.");
    } finally {
      setBusyItemIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  async function handleSaveName(itemId: number) {
    if (!editingName.trim()) {
      setError("Item name cannot be empty.");
      return;
    }
    setBusyItemIds((prev) => new Set(prev).add(itemId));
    setError(null);
    try {
      await api.updateItemName(itemId, editingName.trim());
      setEditingId(null);
      setEditingName("");
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update item.");
    } finally {
      setBusyItemIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  async function handleBulkUpload(files: FileList | null) {
    if (!files || files.length === 0) {
      return;
    }
    setUploadingBulk(true);
    setError(null);
    setBulkAnalysis(null);
    try {
      const response = await api.bulkUploadAndAnalyze(Array.from(files), bulkDefaults);
      await refreshItems();
      const graphEdges = response.analysis?.wardrobe_graph?.edges.length ?? 0;
      const outfitPotential = response.analysis?.outfit_potential ?? 0;
      const topGap = response.analysis?.gap_analysis?.[0]?.suggestion ?? "No gap suggestion available.";
      setBulkAnalysis(
        `${response.uploaded_count} items imported. Outfit potential: ${outfitPotential}. Compatibility links: ${graphEdges}. Next best add: ${topGap}`,
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Bulk upload failed.");
    } finally {
      setUploadingBulk(false);
    }
  }

  async function handleSuggestions() {
    setLoadingSuggestions(true);
    setError(null);
    try {
      const response = await api.getSuggestions(mood, occasion, location);
      setSuggestions(response.suggestions ?? []);
      const factors = response.style_profile?.temporal_state?.state_factors ?? [];
      if (factors.length > 0) {
        setBulkAnalysis((prev) => prev ?? `Adaptive context: ${factors.join(" | ")}`);
      }
      await refreshTemporalState();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to fetch suggestions.");
    } finally {
      setLoadingSuggestions(false);
    }
  }

  async function handleCheckinSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmittingCheckin(true);
    setError(null);
    try {
      const payload: ProfileCheckinCreate = {
        schema_version: "v1",
        life_phase: checkin.life_phase?.trim() || undefined,
        role_transition: checkin.role_transition?.trim() || undefined,
        body_change_note: checkin.body_change_note?.trim() || undefined,
        fit_confidence: checkin.fit_confidence,
        style_goals: splitTags(styleGoalsText),
      };
      await api.createProfileCheckin(payload);
      await refreshTemporalState();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save check-in.");
    } finally {
      setSubmittingCheckin(false);
    }
  }

  async function handleFigurePhotoUpload(file: File | null) {
    if (!file) {
      return;
    }
    setLoadingAnalysis(true);
    setError(null);
    try {
      const result = await api.analyzeFigurePhoto(file);
      setColorAnalysis(
        `${result.season} / ${result.undertone} / contrast ${result.contrast_level} / ${result.palette.join(", ")}`,
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Color analysis failed.");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  return (
    <main className="layout">
      <header className="hero">
        <h1>Wardrobe Intelligence</h1>
        <p>Elegant wardrobe management with efficient suggestions and a clean data flow.</p>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <section className="card">
        <h2>1. Color Profile</h2>
        <label className="field">
          Upload full-body photo
          <input
            type="file"
            accept="image/*"
            onChange={(event) => void handleFigurePhotoUpload(event.target.files?.[0] ?? null)}
            disabled={loadingAnalysis}
          />
        </label>
        <p>{loadingAnalysis ? "Analyzing full figure..." : colorAnalysis ?? "No analysis yet."}</p>
      </section>

      <section className="card">
        <h2>2. Context Check-in</h2>
        <form className="grid" onSubmit={handleCheckinSubmit}>
          <label className="field">
            Life phase
            <input
              placeholder="e.g. student, professional, parent"
              value={checkin.life_phase}
              onChange={(event) => setCheckin((prev) => ({ ...prev, life_phase: event.target.value }))}
            />
          </label>
          <label className="field">
            Role transition
            <input
              placeholder="e.g. student -> professional"
              value={checkin.role_transition}
              onChange={(event) => setCheckin((prev) => ({ ...prev, role_transition: event.target.value }))}
            />
          </label>
          <label className="field">
            Fit confidence (0..1)
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={checkin.fit_confidence ?? 0.6}
              onChange={(event) => setCheckin((prev) => ({ ...prev, fit_confidence: Number(event.target.value) }))}
            />
          </label>
          <label className="field">
            Style goals (comma separated)
            <input value={styleGoalsText} onChange={(event) => setStyleGoalsText(event.target.value)} />
          </label>
          <label className="field">
            Body/Fit note
            <input
              placeholder="e.g. prefers looser fits this season"
              value={checkin.body_change_note}
              onChange={(event) => setCheckin((prev) => ({ ...prev, body_change_note: event.target.value }))}
            />
          </label>
          <button type="submit" disabled={submittingCheckin}>
            {submittingCheckin ? "Saving..." : "Save check-in"}
          </button>
        </form>
        <p>
          {temporalState?.features
            ? `Current context: ${String(temporalState.features["life_phase"] ?? "unspecified")} · confidence ${temporalState.confidence.toFixed(2)}`
            : "No temporal profile yet. Add a check-in to personalize recommendations over time."}
        </p>
      </section>

      <section className="card">
        <h2>3. Add Item</h2>
        <form className="grid" onSubmit={handleCreateItem}>
          <label className="field">
            Name
            <input
              required
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>
          <label className="field">
            Category
            <select
              value={form.category}
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value as WardrobeCategory }))}
            >
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Formality
            <select
              value={form.formality}
              onChange={(event) => setForm((prev) => ({ ...prev, formality: event.target.value as DresscodeLevel }))}
            >
              {dresscodes.map((dresscode) => (
                <option key={dresscode} value={dresscode}>
                  {dresscode}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Color family
            <select
              value={form.color_families[0]}
              onChange={(event) => setForm((prev) => ({ ...prev, color_families: [event.target.value as ColorFamily] }))}
            >
              {colors.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Style tags (comma separated)
            <input value={styleTagsText} onChange={(event) => setStyleTagsText(event.target.value)} />
          </label>
          <label className="field">
            Season tags (comma separated)
            <input value={seasonTagsText} onChange={(event) => setSeasonTagsText(event.target.value)} />
          </label>
          <button type="submit">Save item</button>
        </form>
      </section>

      <section className="card">
        <h2>4. Bulk Upload + Analyze</h2>
        <div className="row">
          <label className="field inline">
            Default category
            <select
              value={bulkDefaults.category}
              onChange={(event) =>
                setBulkDefaults((prev) => ({ ...prev, category: event.target.value as WardrobeCategory }))
              }
            >
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline">
            Default formality
            <select
              value={bulkDefaults.formality}
              onChange={(event) =>
                setBulkDefaults((prev) => ({ ...prev, formality: event.target.value as DresscodeLevel }))
              }
            >
              {dresscodes.map((dresscode) => (
                <option key={dresscode} value={dresscode}>
                  {dresscode}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline">
            Default color
            <select
              value={bulkDefaults.color_family}
              onChange={(event) => setBulkDefaults((prev) => ({ ...prev, color_family: event.target.value as ColorFamily }))}
            >
              {colors.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </label>
          <label className="uploadButton">
            {uploadingBulk ? "Uploading..." : "Upload all clothing photos"}
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => void handleBulkUpload(event.target.files)}
              disabled={uploadingBulk}
            />
          </label>
        </div>
        <p>{bulkAnalysis ?? "Select many photos at once. Filenames become item names automatically."}</p>
      </section>

      <section className="card">
        <h2>5. Wardrobe</h2>
        {loadingItems ? <p>Loading wardrobe...</p> : null}
        {!loadingItems && sortedItems.length === 0 ? <p>No items yet. Add your first piece above.</p> : null}
        <div className="items">
          {sortedItems.map((item) => (
            <article className="item" key={item.id}>
              <div className="thumbWrap">
                {item.image_url ? (
                  <img src={item.image_url} alt={item.name} className="thumb" loading="lazy" />
                ) : (
                  <div className="thumbPlaceholder">No image</div>
                )}
              </div>
              <div>
                {editingId === item.id ? (
                  <div className="row">
                    <input value={editingName} onChange={(event) => setEditingName(event.target.value)} />
                    <button
                      type="button"
                      onClick={() => void handleSaveName(item.id)}
                      disabled={busyItemIds.has(item.id)}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(null);
                        setEditingName("");
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <h3>{item.name}</h3>
                )}
                <p>
                  {item.category} · {item.formality}
                </p>
                <p>{item.color_families.join(", ")}</p>
              </div>
              <div className="actions">
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(item.id);
                    setEditingName(item.name);
                  }}
                  disabled={busyItemIds.has(item.id)}
                >
                  Edit
                </button>
                <label className="uploadButton">
                  Upload image
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => void handleUpload(item.id, event.target.files?.[0] ?? null)}
                    disabled={busyItemIds.has(item.id)}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void handleDelete(item.id)}
                  disabled={busyItemIds.has(item.id)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>6. Suggestions</h2>
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
            Location (optional)
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="e.g. Berlin,de"
            />
          </label>
          <button type="button" onClick={() => void handleSuggestions()} disabled={loadingSuggestions}>
            {loadingSuggestions ? "Generating..." : "Generate top outfits"}
          </button>
        </div>
        {suggestions.length === 0 ? <p>No suggestions loaded yet.</p> : null}
        {temporalState?.state_factors?.length ? (
          <p>Adaptive factors: {temporalState.state_factors.join(" | ")}</p>
        ) : null}
        {suggestions.map((suggestion) => (
          <article key={suggestion.id} className="suggestion">
            <h3>{suggestion.item_names.join(" + ")}</h3>
            <p>Score: {suggestion.total_score.toFixed(3)}</p>
            <p>{suggestion.explanation}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
