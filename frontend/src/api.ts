import type { Suggestion, WardrobeItem, WardrobeItemCreate } from "./types";

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
  getSuggestions: (mood: string, occasion: string) =>
    request<{ suggestions: Suggestion[] }>(
      `/suggestions?mood=${encodeURIComponent(mood)}&occasion=${encodeURIComponent(occasion)}`,
    ),
  analyzeSelfie: (file: File) => {
    const formData = new FormData();
    formData.append("selfie", file);
    return request<{ season: string; undertone: string; contrast_level: string; palette: string[] }>(
      "/profile/color-analysis",
      {
        method: "POST",
        body: formData,
      },
    );
  },
};
