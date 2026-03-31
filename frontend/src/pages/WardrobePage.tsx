import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { trackEvent } from "../telemetry";
import type { ColorFamily, DresscodeLevel, WardrobeCategory, WardrobeItem, WardrobeItemCreate } from "../types";

const categories: WardrobeCategory[] = ["top", "bottom", "outer", "shoes", "accessory"];
const dresscodes: DresscodeLevel[] = ["casual", "smart_casual", "business", "formal"];
const colors: ColorFamily[] = ["neutral", "warm", "cool", "bold", "earth", "pastel"];
const weatherTags = ["cold", "mild", "hot", "rain", "wind", "snow"];

const initialForm: WardrobeItemCreate = {
  name: "",
  category: "top",
  color_families: ["neutral"],
  formality: "casual",
  season_tags: [],
  weather_tags: [],
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

export function WardrobePage() {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [form, setForm] = useState<WardrobeItemCreate>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [styleTagsText, setStyleTagsText] = useState("");
  const [seasonTagsText, setSeasonTagsText] = useState("");
  const [weatherTagsText, setWeatherTagsText] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyItemIds, setBusyItemIds] = useState<Set<number>>(new Set());
  const [uploadingBulk, setUploadingBulk] = useState(false);
  const [bulkResult, setBulkResult] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    category: "" as WardrobeCategory | "",
    color_family: "" as ColorFamily | "",
    weather_tag: "",
    sort_by: "id" as "id" | "name",
    sort_dir: "asc" as "asc" | "desc",
  });

  const sortedItems = useMemo(() => items, [items]);

  async function refreshItems() {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listItemsFiltered(filters);
      setItems(rows);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load wardrobe.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshItems();
  }, [filters.category, filters.color_family, filters.weather_tag, filters.sort_by, filters.sort_dir]);

  async function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.createItem({
        ...form,
        style_tags: splitTags(styleTagsText),
        season_tags: splitTags(seasonTagsText),
        weather_tags: splitTags(weatherTagsText),
      });
      trackEvent("wardrobe_item_created", {
        category: form.category,
        color_family: form.color_families[0],
        source: "manual",
      });
      setForm(initialForm);
      setStyleTagsText("");
      setSeasonTagsText("");
      setWeatherTagsText("");
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create item.");
    }
  }

  async function handleDelete(itemId: number) {
    setBusyItemIds((prev) => new Set(prev).add(itemId));
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
    try {
      await api.uploadImage(itemId, file);
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to upload image.");
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
    setBulkResult(null);
    try {
      const response = await api.bulkUploadAndAnalyze(Array.from(files), {
        category: form.category,
        formality: form.formality,
        color_family: form.color_families[0],
      });
      setBulkResult(`${response.uploaded_count} items uploaded.`);
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Bulk upload failed.");
    } finally {
      setUploadingBulk(false);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Closet Management</p>
      </div>
      <h2>Wardrobe Archive</h2>
      {error ? <p className="error">{error}</p> : null}
      <form className="grid" onSubmit={handleCreateItem}>
        <label className="field">
          Name
          <input required value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
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
          Season notes
          <input placeholder="spring, autumn" value={seasonTagsText} onChange={(event) => setSeasonTagsText(event.target.value)} />
        </label>
        <label className="field">
          Weather notes
          <input placeholder="cold, rain" value={weatherTagsText} onChange={(event) => setWeatherTagsText(event.target.value)} />
        </label>
        <label className="field">
          Style cues
          <input placeholder="classic, minimal" value={styleTagsText} onChange={(event) => setStyleTagsText(event.target.value)} />
        </label>
        <button type="submit">Add piece</button>
      </form>
      <div className="row">
        <label className="uploadButton">
          {uploadingBulk ? "Uploading..." : "Bulk import"}
          <input type="file" accept="image/*" multiple onChange={(event) => void handleBulkUpload(event.target.files)} />
        </label>
        <label className="field inline">
          Filter by category
          <select value={filters.category} onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value as WardrobeCategory | "" }))}>
            <option value="">all</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
        <label className="field inline">
          Filter by color
          <select value={filters.color_family} onChange={(event) => setFilters((prev) => ({ ...prev, color_family: event.target.value as ColorFamily | "" }))}>
            <option value="">all</option>
            {colors.map((color) => (
              <option key={color} value={color}>
                {color}
              </option>
            ))}
          </select>
        </label>
        <label className="field inline">
          Filter by weather
          <select value={filters.weather_tag} onChange={(event) => setFilters((prev) => ({ ...prev, weather_tag: event.target.value }))}>
            <option value="">all</option>
            {weatherTags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>
        </label>
        <label className="field inline">
          Sort by
          <select value={filters.sort_by} onChange={(event) => setFilters((prev) => ({ ...prev, sort_by: event.target.value as "id" | "name" }))}>
            <option value="id">id</option>
            <option value="name">name</option>
          </select>
        </label>
      </div>
      {bulkResult ? <p className="metaNote">{bulkResult}</p> : null}
      {loading ? <p className="metaNote">Loading wardrobe...</p> : null}
      {!loading && sortedItems.length === 0 ? (
        <div className="emptyState">
          <h3>Your wardrobe is still empty</h3>
          <p>Start with 3-5 core pieces or use bulk import so Daily Edit can generate meaningful combinations.</p>
        </div>
      ) : null}
      <div className="items">
        {sortedItems.map((item) => (
          <article className="item" key={item.id}>
            <div className="thumbWrap">
              {item.image_url ? (
                <img src={item.image_url} alt={item.name} className="thumb" />
              ) : (
                <div className="thumbPlaceholder">No image</div>
              )}
            </div>
            <div>
              <h3>{item.name}</h3>
              <p>
                {item.category} · {item.formality}
              </p>
              <p>Color: {item.color_families.join(", ")}</p>
              <p>Weather: {item.weather_tags.join(", ") || "none"}</p>
            </div>
            <div className="actions">
              <label className="uploadButton">
                Upload image
                <input type="file" accept="image/*" onChange={(event) => void handleUpload(item.id, event.target.files?.[0] ?? null)} />
              </label>
              <button type="button" onClick={() => void handleDelete(item.id)} disabled={busyItemIds.has(item.id)}>
                Remove piece
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
