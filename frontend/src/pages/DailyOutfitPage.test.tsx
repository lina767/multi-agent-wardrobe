import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DailyOutfitPage } from "./DailyOutfitPage";

vi.mock("../api", () => ({
  api: {
    getSuggestions: vi.fn(async () => ({
      suggestions: [],
      context: {},
    })),
    getWardrobeAnalytics: vi.fn(async () => ({
      gap_analysis: [
        {
          suggestion: "Dir fehlt ein vielseitiger schwarzer blazer, der 12 deiner Stuecke aufwerten wuerde.",
          target_item_archetype: "blazer",
          suggested_color: "schwarz",
          upgrade_count: 12,
          estimated_new_outfits: 8,
          impacted_item_ids: [1, 2, 3],
          confidence: 0.78,
          reason: "Slot bottleneck with broad cross-category compatibility.",
        },
      ],
    })),
    listItems: vi.fn(async () => []),
    sendSuggestionFeedback: vi.fn(async () => ({ status: "updated" })),
    logOutfit: vi.fn(async () => ({ id: 1, status: "logged" })),
    updateItem: vi.fn(async () => ({})),
  },
}));

describe("DailyOutfitPage gap panel", () => {
  it("renders structured gap analysis after generation", async () => {
    render(<DailyOutfitPage />);
    fireEvent.click(screen.getByRole("button", { name: /Generate top 3/i }));
    await waitFor(() => {
      expect(screen.getByText(/Gap analysis:/i)).toBeTruthy();
      expect(screen.getByText(/items upgraded/i)).toBeTruthy();
      expect(screen.getByText(/confidence/i)).toBeTruthy();
    });
  });
});
