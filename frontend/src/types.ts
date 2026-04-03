export type WardrobeCategory = "top" | "bottom" | "outer" | "shoes" | "accessory";
export type DresscodeLevel = "casual" | "smart_casual" | "business" | "formal";
export type ColorFamily = "neutral" | "warm" | "cool" | "bold" | "earth" | "pastel";
export type LaundryStatus = "clean" | "dirty" | "dry_cleaning";
export type FitType = "oversized" | "regular" | "slim" | "cropped";
export type MaterialType = "cotton" | "silk" | "wool" | "synthetic" | "linen";
export type WearFrequency = "rarely" | "sometimes" | "often" | "very_often";
export type ItemCondition = "new" | "good" | "worn" | "needs_repair";

export interface MaterialInsights {
  care: string;
  weather: string;
  texture_match: string;
}

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
  fit_type: FitType;
  material?: MaterialType | null;
  wear_frequency: WearFrequency;
  last_worn_at?: string | null;
  condition: ItemCondition;
  material_insights?: MaterialInsights | null;
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
  fit_type: FitType;
  material?: MaterialType;
  wear_frequency: WearFrequency;
  last_worn_at?: string;
  condition: ItemCondition;
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
    gap_analysis?: GapAnalysisEntry[];
  } | null;
}

export interface GapAnalysisEntry {
  suggestion: string;
  target_item_archetype?: string;
  suggested_color?: string;
  upgrade_count?: number;
  estimated_new_outfits: number;
  impacted_item_ids?: number[];
  confidence?: number;
  reason: string;
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

export interface SuggestionFeedbackPayload {
  accepted?: boolean;
  rating?: number;
  occasion?: string;
  thumb?: "up" | "down";
  reason_tags?: string[];
  context?: Record<string, unknown>;
}

export interface QuickSuggestionsResponse {
  context: {
    occasion?: string;
    mood?: string;
    weather?: {
      temperature_c?: number;
      condition?: string;
      rain_probability?: number;
      uv_index?: number;
      forecast_summary?: string;
    };
  };
  suggestions: Array<{
    item_ids: number[];
    item_names: string[];
    total_score: number;
    explanation: string;
  }>;
  scientific_note: string;
}

export interface ProactiveSuggestionsResponse {
  generated_at: string;
  entries: Array<{
    event: {
      title: string;
      starts_at: string;
      location?: string | null;
      event_type: string;
      source: string;
    };
    suggestions: Array<{
      item_ids: number[];
      item_names: string[];
      total_score: number;
      explanation: string;
    }>;
  }>;
}

export interface PackingAssistantResponse {
  summary: {
    duration_days: number;
    planned_occasions: string[];
    coverage_ratio: number;
    selected_item_count: number;
    laundry_frequency_days: number;
  };
  packing_item_ids: number[];
  packing_item_names: string[];
  outfit_plan: Array<{
    day: number;
    occasion: string;
    item_ids: number[];
    item_names: string[];
    score: number;
  }>;
}

export interface WardrobeAnalyticsResponse {
  outfit_potential?: number;
  capsule_suggestions?: Array<{ formula: string; status: Record<string, number> }>;
  gap_analysis?: GapAnalysisEntry[];
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
