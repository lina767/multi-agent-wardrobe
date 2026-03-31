export type WardrobeCategory = "top" | "bottom" | "outer" | "shoes" | "accessory";
export type DresscodeLevel = "casual" | "smart_casual" | "business" | "formal";
export type ColorFamily = "neutral" | "warm" | "cool" | "bold" | "earth" | "pastel";

export interface WardrobeItem {
  id: number;
  user_id: number;
  name: string;
  category: WardrobeCategory;
  color_families: ColorFamily[];
  formality: DresscodeLevel;
  season_tags: string[];
  is_available: boolean;
  style_tags: string[];
  brand?: string | null;
  size_label?: string | null;
  material?: string | null;
  quantity: number;
  purchase_price?: number | null;
  notes?: string | null;
  image_url?: string | null;
}

export interface WardrobeItemCreate {
  name: string;
  category: WardrobeCategory;
  color_families: ColorFamily[];
  formality: DresscodeLevel;
  season_tags: string[];
  is_available: boolean;
  style_tags: string[];
  brand?: string;
  size_label?: string;
  material?: string;
  quantity: number;
  purchase_price?: number;
  notes?: string;
}

export interface Suggestion {
  id: number;
  items: number[];
  item_names: string[];
  total_score: number;
  explanation: string;
}
