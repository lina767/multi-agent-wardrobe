import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, resolveApiAssetUrl } from "../api";
import type {
  ColorFamily,
  DresscodeLevel,
  FitType,
  ItemCondition,
  LaundryStatus,
  MaterialType,
  WardrobeCategory,
  WardrobeItem,
  WardrobeItemCreate,
  WearFrequency,
} from "../types";

const categories: WardrobeCategory[] = ["top", "bottom", "outer", "shoes", "accessory"];
const dresscodes: DresscodeLevel[] = ["sport", "casual", "smart_casual", "business", "formal"];
const colors: ColorFamily[] = ["neutral", "warm", "cool", "bold", "earth", "pastel"];
const weatherTags = ["cold", "mild", "hot", "rain", "wind", "snow"];
const laundryStatuses: LaundryStatus[] = ["clean", "dirty", "dry_cleaning"];
const fitTypes: FitType[] = ["oversized", "regular", "slim", "cropped"];
const materialTypes: MaterialType[] = ["cotton", "silk", "wool", "synthetic", "linen", "jeans"];
const wearFrequencies: WearFrequency[] = ["rarely", "sometimes", "often", "very_often"];
const itemConditions: ItemCondition[] = ["new", "good", "worn", "needs_repair"];

const initialForm: WardrobeItemCreate = {
  name: "",
  category: "top",
  color_families: ["neutral"],
  formality: "casual",
  season_tags: [],
  weather_tags: [],
  is_available: true,
  status: "clean",
  style_tags: [],
  size_label: "",
  fit_type: "regular",
  material: "cotton",
  wear_frequency: "sometimes",
  condition: "good",
  quantity: 1,
};

function splitTags(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

type ItemEditDraft = {
  name: string;
  category: WardrobeCategory;
  formality: DresscodeLevel;
  color_family: ColorFamily;
  season_tags_text: string;
  weather_tags_text: string;
  status: LaundryStatus;
  style_tags_text: string;
  size_label: string;
  fit_type: FitType;
  material: MaterialType;
  wear_frequency: WearFrequency;
  last_worn_at: string;
  condition: ItemCondition;
};

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
  const [uploadingSinglePhoto, setUploadingSinglePhoto] = useState(false);
  const [bulkResult, setBulkResult] = useState<string | null>(null);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<ItemEditDraft | null>(null);
  const [filters, setFilters] = useState({
    category: "" as WardrobeCategory | "",
    color_family: "" as ColorFamily | "",
    weather_tag: "",
    status: "" as LaundryStatus | "",
    condition: "" as ItemCondition | "",
    wear_frequency: "" as WearFrequency | "",
    fit_type: "" as FitType | "",
    sort_by: "id" as "id" | "name",
    sort_dir: "asc" as "asc" | "desc",
  });

  const sortedItems = useMemo(() => items, [items]);
  const availableCount = useMemo(() => items.filter((item) => item.status === "clean").length, [items]);

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
  }, [filters.category, filters.color_family, filters.weather_tag, filters.status, filters.condition, filters.wear_frequency, filters.fit_type, filters.sort_by, filters.sort_dir]);

  async function handleStatusUpdate(itemId: number, status: LaundryStatus) {
    setBusyItemIds((prev) => new Set(prev).add(itemId));
    setError(null);
    try {
      await api.updateItem(itemId, {
        status,
        is_available: status === "clean",
      });
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update item status.");
    } finally {
      setBusyItemIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  function startEdit(item: WardrobeItem) {
    setEditingItemId(item.id);
    setEditDraft({
      name: item.name,
      category: item.category,
      formality: item.formality,
      color_family: item.color_families[0] ?? "neutral",
      season_tags_text: item.season_tags.join(", "),
      weather_tags_text: item.weather_tags.join(", "),
      status: item.status,
      style_tags_text: item.style_tags.join(", "),
      size_label: item.size_label ?? "",
      fit_type: item.fit_type,
      material: item.material ?? "cotton",
      wear_frequency: item.wear_frequency,
      last_worn_at: item.last_worn_at ? item.last_worn_at.slice(0, 10) : "",
      condition: item.condition,
    });
  }

  function cancelEdit() {
    setEditingItemId(null);
    setEditDraft(null);
  }

  async function handleSaveItemDetails(itemId: number) {
    if (!editDraft) {
      return;
    }
    setBusyItemIds((prev) => new Set(prev).add(itemId));
    setError(null);
    try {
      const statusValue = editDraft.status;
      await api.updateItem(itemId, {
        name: editDraft.name.trim(),
        category: editDraft.category,
        formality: editDraft.formality,
        color_families: [editDraft.color_family],
        season_tags: splitTags(editDraft.season_tags_text),
        weather_tags: splitTags(editDraft.weather_tags_text),
        status: statusValue,
        style_tags: splitTags(editDraft.style_tags_text),
        size_label: editDraft.size_label.trim(),
        fit_type: editDraft.fit_type,
        material: editDraft.material,
        wear_frequency: editDraft.wear_frequency,
        last_worn_at: editDraft.last_worn_at || undefined,
        condition: editDraft.condition,
        is_available: statusValue === "clean",
      });
      cancelEdit();
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save item details.");
    } finally {
      setBusyItemIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

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

  async function handleAddFromPhoto(file: File | null) {
    if (!file) {
      return;
    }
    setUploadingSinglePhoto(true);
    setError(null);
    setBulkResult(null);
    try {
      const response = await api.bulkUploadAndAnalyze([file], {
        category: form.category,
        formality: form.formality,
        color_family: form.color_families[0],
      });
      const uploaded = response.items?.[0];
      setBulkResult(uploaded ? `Added from photo: ${uploaded.name}` : "Added 1 item from photo.");
      await refreshItems();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Photo upload failed.");
    } finally {
      setUploadingSinglePhoto(false);
    }
  }

  return (
    <section className="card pageSection wardrobePage">
      <header className="wardrobeHeader">
        <div className="sectionHead">
          <p className="eyebrow">Closet Management</p>
          <p className="metaNote">{items.length} pieces loaded</p>
        </div>
        <h2>Wardrobe Archive</h2>
        <p className="metaNote wardrobeIntro">Add pieces, upload photos, and keep laundry status up to date for better daily recommendations.</p>
        <div className="wardrobeSummary row">
          <span className="guideStep done">Ready to wear: {availableCount}</span>
          <span className="guideStep">Needs care: {Math.max(0, items.length - availableCount)}</span>
        </div>
      </header>
      {error ? <p className="error">{error}</p> : null}
      <section className="card wardrobeBlock wardrobeComposer">
        <div className="sectionHead">
          <p className="eyebrow">Add Piece</p>
        </div>
        <p className="metaNote">Quick add: upload one clothing photo and we create the piece automatically.</p>
        <label className="uploadButton wardrobeAddFromPhotoButton">
          {uploadingSinglePhoto ? "Adding from photo..." : "Add piece from photo"}
          <input type="file" accept="image/*" onChange={(event) => void handleAddFromPhoto(event.target.files?.[0] ?? null)} />
        </label>
        <form className="grid wardrobeFormGrid" onSubmit={handleCreateItem}>
          <label className="field">
            Name
            <input required value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
          </label>
          <label className="field">
            Category
            <select value={form.category} onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value as WardrobeCategory }))}>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Formality
            <select value={form.formality} onChange={(event) => setForm((prev) => ({ ...prev, formality: event.target.value as DresscodeLevel }))}>
              {dresscodes.map((dresscode) => (
                <option key={dresscode} value={dresscode}>
                  {dresscode}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Color family
            <select value={form.color_families[0]} onChange={(event) => setForm((prev) => ({ ...prev, color_families: [event.target.value as ColorFamily] }))}>
              {colors.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Size
            <input value={form.size_label ?? ""} onChange={(event) => setForm((prev) => ({ ...prev, size_label: event.target.value }))} />
          </label>
          <label className="field">
            Fit type
            <select value={form.fit_type} onChange={(event) => setForm((prev) => ({ ...prev, fit_type: event.target.value as FitType }))}>
              {fitTypes.map((fitType) => (
                <option key={fitType} value={fitType}>
                  {fitType}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Material
            <select value={form.material ?? "cotton"} onChange={(event) => setForm((prev) => ({ ...prev, material: event.target.value as MaterialType }))}>
              {materialTypes.map((materialType) => (
                <option key={materialType} value={materialType}>
                  {materialType}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Wear frequency
            <select value={form.wear_frequency} onChange={(event) => setForm((prev) => ({ ...prev, wear_frequency: event.target.value as WearFrequency }))}>
              {wearFrequencies.map((wearFrequency) => (
                <option key={wearFrequency} value={wearFrequency}>
                  {wearFrequency}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Condition
            <select value={form.condition} onChange={(event) => setForm((prev) => ({ ...prev, condition: event.target.value as ItemCondition }))}>
              {itemConditions.map((itemCondition) => (
                <option key={itemCondition} value={itemCondition}>
                  {itemCondition}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Last worn
            <input
              type="date"
              value={form.last_worn_at?.slice(0, 10) ?? ""}
              onChange={(event) => setForm((prev) => ({ ...prev, last_worn_at: event.target.value || undefined }))}
            />
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
          <button className="wardrobePrimaryButton" type="submit">
            Add piece
          </button>
        </form>
      </section>
      <section className="card wardrobeBlock wardrobeControls">
        <div className="sectionHead">
          <p className="eyebrow">Import & Filter</p>
        </div>
        <div className="wardrobeControlsGrid">
          <label className="uploadButton wardrobeBulkUpload">
            {uploadingBulk ? "Uploading..." : "Bulk import"}
            <input type="file" accept="image/*" multiple onChange={(event) => void handleBulkUpload(event.target.files)} />
          </label>
          <label className="field inline wardrobeFilterField">
            Category
            <select value={filters.category} onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value as WardrobeCategory | "" }))}>
              <option value="">all</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Color
            <select value={filters.color_family} onChange={(event) => setFilters((prev) => ({ ...prev, color_family: event.target.value as ColorFamily | "" }))}>
              <option value="">all</option>
              {colors.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Weather
            <select value={filters.weather_tag} onChange={(event) => setFilters((prev) => ({ ...prev, weather_tag: event.target.value }))}>
              <option value="">all</option>
              {weatherTags.map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Laundry
            <select value={filters.status} onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value as LaundryStatus | "" }))}>
              <option value="">all</option>
              {laundryStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Condition
            <select value={filters.condition} onChange={(event) => setFilters((prev) => ({ ...prev, condition: event.target.value as ItemCondition | "" }))}>
              <option value="">all</option>
              {itemConditions.map((itemCondition) => (
                <option key={itemCondition} value={itemCondition}>
                  {itemCondition}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Frequency
            <select value={filters.wear_frequency} onChange={(event) => setFilters((prev) => ({ ...prev, wear_frequency: event.target.value as WearFrequency | "" }))}>
              <option value="">all</option>
              {wearFrequencies.map((wearFrequency) => (
                <option key={wearFrequency} value={wearFrequency}>
                  {wearFrequency}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeFilterField">
            Fit
            <select value={filters.fit_type} onChange={(event) => setFilters((prev) => ({ ...prev, fit_type: event.target.value as FitType | "" }))}>
              <option value="">all</option>
              {fitTypes.map((fitType) => (
                <option key={fitType} value={fitType}>
                  {fitType}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline wardrobeSortField">
            Sort by
            <select value={filters.sort_by} onChange={(event) => setFilters((prev) => ({ ...prev, sort_by: event.target.value as "id" | "name" }))}>
              <option value="id">id</option>
              <option value="name">name</option>
            </select>
          </label>
          <label className="field inline wardrobeSortField">
            Direction
            <select value={filters.sort_dir} onChange={(event) => setFilters((prev) => ({ ...prev, sort_dir: event.target.value as "asc" | "desc" }))}>
              <option value="asc">asc</option>
              <option value="desc">desc</option>
            </select>
          </label>
          <button
            className="wardrobeResetButton"
            type="button"
            onClick={() =>
              setFilters({
                category: "",
                color_family: "",
                weather_tag: "",
                status: "",
                condition: "",
                wear_frequency: "",
                fit_type: "",
                sort_by: "id",
                sort_dir: "asc",
              })
            }
          >
            Reset filters
          </button>
        </div>
      </section>
      <section className="wardrobeList">
        <div className="sectionHead">
          <p className="eyebrow">Your Pieces</p>
        </div>
        {bulkResult ? <p className="metaNote">{bulkResult}</p> : null}
        {loading ? <p className="metaNote">Loading wardrobe...</p> : null}
        {!loading && sortedItems.length === 0 ? (
          <div className="emptyState wardrobeEmptyState">
            <h3>Your wardrobe is still empty</h3>
            <p>Start with 3-5 core pieces or use bulk import so Daily Edit can generate meaningful combinations.</p>
          </div>
        ) : null}
        <div className="items wardrobeItems">
          {sortedItems.map((item) => (
            <article className="item wardrobeItem" key={item.id}>
              <div className="thumbWrap">
                {item.image_url ? (
                  <img src={resolveApiAssetUrl(item.image_url) ?? item.image_url} alt={item.name} className="thumb" />
                ) : (
                  <div className="thumbPlaceholder">No image</div>
                )}
              </div>
              <div className="wardrobeItemBody">
                {editingItemId === item.id && editDraft ? (
                  <>
                    <label className="field">
                      Name
                      <input value={editDraft.name} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, name: event.target.value } : prev))} />
                    </label>
                    <label className="field inline">
                      Category
                      <select value={editDraft.category} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, category: event.target.value as WardrobeCategory } : prev))}>
                        {categories.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Formality
                      <select value={editDraft.formality} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, formality: event.target.value as DresscodeLevel } : prev))}>
                        {dresscodes.map((dresscode) => (
                          <option key={dresscode} value={dresscode}>
                            {dresscode}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Color
                      <select value={editDraft.color_family} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, color_family: event.target.value as ColorFamily } : prev))}>
                        {colors.map((color) => (
                          <option key={color} value={color}>
                            {color}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Size
                      <input value={editDraft.size_label} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, size_label: event.target.value } : prev))} />
                    </label>
                    <label className="field inline">
                      Fit type
                      <select value={editDraft.fit_type} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, fit_type: event.target.value as FitType } : prev))}>
                        {fitTypes.map((fitType) => (
                          <option key={fitType} value={fitType}>
                            {fitType}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Material
                      <select value={editDraft.material} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, material: event.target.value as MaterialType } : prev))}>
                        {materialTypes.map((materialType) => (
                          <option key={materialType} value={materialType}>
                            {materialType}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Frequency
                      <select value={editDraft.wear_frequency} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, wear_frequency: event.target.value as WearFrequency } : prev))}>
                        {wearFrequencies.map((wearFrequency) => (
                          <option key={wearFrequency} value={wearFrequency}>
                            {wearFrequency}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field inline">
                      Condition
                      <select value={editDraft.condition} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, condition: event.target.value as ItemCondition } : prev))}>
                        {itemConditions.map((itemCondition) => (
                          <option key={itemCondition} value={itemCondition}>
                            {itemCondition}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      Last worn
                      <input type="date" value={editDraft.last_worn_at} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, last_worn_at: event.target.value } : prev))} />
                    </label>
                    <label className="field">
                      Season tags
                      <input placeholder="spring, autumn" value={editDraft.season_tags_text} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, season_tags_text: event.target.value } : prev))} />
                    </label>
                    <label className="field">
                      Weather tags
                      <input placeholder="cold, rain" value={editDraft.weather_tags_text} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, weather_tags_text: event.target.value } : prev))} />
                    </label>
                    <label className="field">
                      Style tags
                      <input placeholder="classic, minimal" value={editDraft.style_tags_text} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, style_tags_text: event.target.value } : prev))} />
                    </label>
                    <label className="field inline">
                      Laundry
                      <select value={editDraft.status} onChange={(event) => setEditDraft((prev) => (prev ? { ...prev, status: event.target.value as LaundryStatus } : prev))}>
                        {laundryStatuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                ) : (
                  <>
                    <h3>{item.name}</h3>
                    <p>
                      {item.category} · {item.formality} · {item.fit_type}
                    </p>
                    <p>Color: {item.color_families.join(", ")}</p>
                    <p>Size: {item.size_label || "n/a"} · Material: {item.material ?? "n/a"}</p>
                    <p>Condition: {item.condition} · Frequency: {item.wear_frequency}</p>
                    <p>Last worn: {item.last_worn_at ? item.last_worn_at.slice(0, 10) : "not set"}</p>
                    <p>Weather: {item.weather_tags.join(", ") || "none"}</p>
                    <p>Laundry: {item.status}</p>
                    {item.material_insights ? (
                      <div className="metaNote wardrobeMaterialInsights">
                        <p>Care: {item.material_insights.care}</p>
                        <p>Weather fit: {item.material_insights.weather}</p>
                        <p>Texture match: {item.material_insights.texture_match}</p>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
              <div className="actions wardrobeItemActions">
                {editingItemId === item.id ? (
                  <>
                    <button type="button" onClick={() => void handleSaveItemDetails(item.id)} disabled={busyItemIds.has(item.id) || !editDraft?.name.trim()}>
                      Save changes
                    </button>
                    <button type="button" onClick={cancelEdit} disabled={busyItemIds.has(item.id)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <label className="field inline">
                      Status
                      <select value={item.status} disabled={busyItemIds.has(item.id)} onChange={(event) => void handleStatusUpdate(item.id, event.target.value as LaundryStatus)}>
                        {laundryStatuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button type="button" onClick={() => startEdit(item)} disabled={busyItemIds.has(item.id) || (editingItemId !== null && editingItemId !== item.id)}>
                      Edit details
                    </button>
                  </>
                )}
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
    </section>
  );
}
