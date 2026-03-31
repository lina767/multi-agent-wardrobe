import type {
  BulkUploadResponse,
  ColorFamily,
  DresscodeLevel,
  ProfileCheckinCreate,
  ProfileCheckinRead,
  Suggestion,
  TemporalState,
  WardrobeCategory,
  WardrobeItem,
  WardrobeItemCreate,
} from "./types";

const API_BASE = (window as Window & { __API_BASE__?: string }).__API_BASE__ ?? "";
const API_PREFIX = `${API_BASE}/api/v1`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, init);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep generic message when response is not JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const api = {
  listItems: () => request<WardrobeItem[]>("/wardrobe/items"),
  createItem: (payload: WardrobeItemCreate) =>
    request<WardrobeItem>("/wardrobe/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deleteItem: async (itemId: number) => {
    await request<unknown>(`/wardrobe/items/${itemId}`, { method: "DELETE" });
  },
  updateItemName: (itemId: number, name: string) =>
    request<WardrobeItem>(`/wardrobe/items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  uploadImage: (itemId: number, file: File) => {
    const formData = new FormData();
    formData.append("image", file);
    return request<WardrobeItem>(`/wardrobe/items/${itemId}/image`, {
      method: "POST",
      body: formData,
    });
  },
  bulkUploadAndAnalyze: (
    files: File[],
    defaults: { category: WardrobeCategory; formality: DresscodeLevel; color_family: ColorFamily },
  ) => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("images", file);
    }
    formData.append("analyze", "true");
    formData.append("category", defaults.category);
    formData.append("formality", defaults.formality);
    formData.append("color_family", defaults.color_family);
    return request<BulkUploadResponse>("/wardrobe/bulk-upload", {
      method: "POST",
      body: formData,
    });
  },
  getSuggestions: (mood: string, occasion: string, location?: string) =>
    request<{
      suggestions: Suggestion[];
      style_profile?: {
        temporal_state?: {
          life_phase?: string;
          dominant_occasion?: string;
          fit_confidence?: number;
          state_factors?: string[];
        };
        dynamic_weights?: Record<string, number>;
      };
    }>(
      (() => {
      const query = new URLSearchParams({
        mood,
        occasion,
      });
      if (location?.trim()) {
        query.set("location", location.trim());
      }
      return `/suggestions?${query.toString()}`;
      })(),
    ),
  createProfileCheckin: (payload: ProfileCheckinCreate) =>
    request<ProfileCheckinRead>("/profile/checkins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getProfileState: () => request<TemporalState>("/profile/state"),
  analyzeFigurePhoto: (file: File) => {
    const formData = new FormData();
    formData.append("photo", file);
    return request<{ season: string; undertone: string; contrast_level: string; palette: string[] }>(
      "/profile/color-analysis",
      {
        method: "POST",
        body: formData,
      },
    );
  },
};
