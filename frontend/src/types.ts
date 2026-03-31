export type WardrobeCategory = "top" | "bottom" | "outer" | "shoes" | "accessory";
export type DresscodeLevel = "casual" | "smart_casual" | "business" | "formal";
export type ColorFamily = "neutral" | "warm" | "cool" | "bold" | "earth" | "pastel";
export type LaundryStatus = "clean" | "dirty" | "dry_cleaning";

export interface WardrobeItem {
  id: number;
  user_id: number;
  name: string;
  category: WardrobeCategory;
  color_families: ColorFamily[];
  formality: DresscodeLevel;
  season_tags: string[];
  weather_tags: string[];
  is_available: boolean;
  status: LaundryStatus;
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
  weather_tags: string[];
  is_available: boolean;
  status: LaundryStatus;
  style_tags: string[];
  brand?: string;
  size_label?: string;
  material?: string;
  quantity: number;
  purchase_price?: number;
  notes?: string;
}

export interface BulkUploadResponse {
  uploaded_count: number;
  items: WardrobeItem[];
  analysis: {
    wardrobe_graph?: { nodes: Array<{ item_id: number; category: string }>; edges: Array<{ left: number; right: number; compatibility: number }> };
    outfit_potential?: number;
    capsule_suggestions?: Array<{ formula: string; status: Record<string, number> }>;
    gap_analysis?: Array<{ suggestion: string; estimated_new_outfits: number; reason: string }>;
  } | null;
}

export interface Suggestion {
  id: number;
  items: number[];
  item_names: string[];
  total_score: number;
  explanation: string;
  reasoning_breakdown?: {
    color_score?: number;
    style_score?: number;
    context_score?: number;
    mood_alignment?: number;
    sustainability?: number;
  };
  evidence_tags?: Array<{
    evidence_id: string;
    citation_short: string;
    effect_on_total: number;
    rationale: string;
  }>;
}

export interface SuggestionsResponse {
  context?: {
    mood?: string;
    occasion?: string;
    weather?: {
      condition?: string;
      condition_raw?: string;
      temperature_c?: number;
      feels_like_c?: number;
      rain_probability?: number;
      uv_index?: number;
      wind_speed_kph?: number;
      forecast_summary?: string;
    };
  };
  suggestions: Suggestion[];
  color_profile?: {
    season?: string;
    undertone?: string;
    contrast_level?: string;
    palette?: string[];
  };
  scientific_note?: string;
  style_profile?: {
    temporal_state?: {
      life_phase?: string;
      dominant_occasion?: string;
      fit_confidence?: number;
      state_factors?: string[];
    };
    dynamic_weights?: Record<string, number>;
  };
}

export interface WardrobeAnalyticsResponse {
  outfit_potential?: number;
  capsule_suggestions?: Array<{ formula: string; status: Record<string, number> }>;
  gap_analysis?: Array<{ suggestion: string; estimated_new_outfits: number; reason: string }>;
}

export interface ProfileCheckinCreate {
  schema_version?: string;
  life_phase?: string;
  role_transition?: string;
  body_change_note?: string;
  fit_confidence?: number;
  style_goals?: string[];
  context_weights?: Record<string, number>;
}

export interface ProfileCheckinRead {
  id: number;
  user_id: number;
  schema_version: string;
  life_phase?: string | null;
  role_transition?: string | null;
  body_change_note?: string | null;
  fit_confidence?: number | null;
  style_goals_json: string[];
  context_weights_json?: Record<string, number> | null;
  effective_from: string;
  created_at: string;
}

export interface TemporalState {
  user_id: number;
  state_key: string;
  features: Record<string, unknown>;
  dynamic_weights: Record<string, number>;
  state_factors: string[];
  confidence: number;
  updated_at: string;
}

export interface UserProfile {
  name: string | null;
  age: number | null;
  life_phase: string | null;
  cold_sensitivity: number | null;
  selfie_url: string | null;
  figure_analysis: string | null;
  color_profile: {
    season?: string;
    undertone?: string;
    contrast_level?: string;
    palette?: string[];
  } | null;
}

export interface OnboardingResponse {
  profile: UserProfile;
  temporal_state: TemporalState;
  suggestions: Array<{
    item_names: string[];
    total_score: number;
    explanation: string;
  }>;
}
