import type {
  BulkUploadResponse,
  ColorFamily,
  DresscodeLevel,
  OnboardingResponse,
  ProfileCheckinCreate,
  ProfileCheckinRead,
  SuggestionsResponse,
  TemporalState,
  UserProfile,
  WardrobeCategory,
  WardrobeItem,
  WardrobeItemCreate,
} from "./types";

const API_BASE = (window as Window & { __API_BASE__?: string }).__API_BASE__ ?? "";
const API_PREFIX = `${API_BASE}/api/v1`;
let apiAccessToken: string | null = null;

export function setApiAccessToken(token: string | null) {
  apiAccessToken = token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? undefined);
  if (apiAccessToken) {
    headers.set("Authorization", `Bearer ${apiAccessToken}`);
  }
  const response = await fetch(`${API_PREFIX}${path}`, { ...init, headers });
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
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  me: () =>
    request<{
      id: number;
      email: string | null;
      display_name: string | null;
      supabase_user_id: string | null;
      is_active: boolean;
    }>("/auth/me"),
  listItems: () => request<WardrobeItem[]>("/wardrobe/items"),
  listItemsFiltered: (filters: {
    category?: WardrobeCategory | "";
    color_family?: ColorFamily | "";
    weather_tag?: string;
    sort_by?: "id" | "name";
    sort_dir?: "asc" | "desc";
  }) => {
    const query = new URLSearchParams();
    if (filters.category) {
      query.set("category", filters.category);
    }
    if (filters.color_family) {
      query.set("color_family", filters.color_family);
    }
    if (filters.weather_tag?.trim()) {
      query.set("weather_tag", filters.weather_tag.trim());
    }
    if (filters.sort_by) {
      query.set("sort_by", filters.sort_by);
    }
    if (filters.sort_dir) {
      query.set("sort_dir", filters.sort_dir);
    }
    const suffix = query.size ? `?${query.toString()}` : "";
    return request<WardrobeItem[]>(`/wardrobe/items${suffix}`);
  },
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
    request<SuggestionsResponse>(
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
  getProfile: () => request<UserProfile>("/profile/me"),
  updateProfile: (payload: { name?: string; age?: number; life_phase?: string; figure_analysis?: string }) =>
    request<UserProfile>("/profile/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  uploadProfileSelfie: (file: File) => {
    const formData = new FormData();
    formData.append("selfie", file);
    return request<UserProfile>("/profile/selfie", {
      method: "POST",
      body: formData,
    });
  },
  updateEmail: (email: string) =>
    request<{ id: number; email: string | null }>("/settings/email", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }),
  runOnboarding: (payload: {
    name?: string;
    age?: number;
    life_phase?: string;
    figure_analysis?: string;
    location?: string;
  }) =>
    request<OnboardingResponse>("/profile/onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
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
