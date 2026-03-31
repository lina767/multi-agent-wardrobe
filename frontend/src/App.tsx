import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type { ColorFamily, DresscodeLevel, Suggestion, WardrobeCategory, WardrobeItem, WardrobeItemCreate } from "./types";

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
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [colorAnalysis, setColorAnalysis] = useState<string | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");

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
  }, []);

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

  async function handleSuggestions() {
    setLoadingSuggestions(true);
    setError(null);
    try {
      const response = await api.getSuggestions(mood, occasion);
      setSuggestions(response.suggestions ?? []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to fetch suggestions.");
    } finally {
      setLoadingSuggestions(false);
    }
  }

  async function handleSelfieUpload(file: File | null) {
    if (!file) {
      return;
    }
    setLoadingAnalysis(true);
    setError(null);
    try {
      const result = await api.analyzeSelfie(file);
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
          Upload selfie
          <input
            type="file"
            accept="image/*"
            onChange={(event) => void handleSelfieUpload(event.target.files?.[0] ?? null)}
            disabled={loadingAnalysis}
          />
        </label>
        <p>{loadingAnalysis ? "Analyzing..." : colorAnalysis ?? "No analysis yet."}</p>
      </section>

      <section className="card">
        <h2>2. Add Item</h2>
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
        <h2>3. Wardrobe</h2>
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
        <h2>4. Suggestions</h2>
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
          <button type="button" onClick={() => void handleSuggestions()} disabled={loadingSuggestions}>
            {loadingSuggestions ? "Generating..." : "Generate top outfits"}
          </button>
        </div>
        {suggestions.length === 0 ? <p>No suggestions loaded yet.</p> : null}
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
