import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";

vi.stubGlobal("fetch", vi.fn(async (url: string) => {
  if (url.includes("/wardrobe/items")) {
    return {
      ok: true,
      json: async () => [],
    };
  }
  return {
    ok: true,
    json: async () => ({ suggestions: [] }),
  };
}) as unknown as typeof fetch);

describe("App", () => {
  it("renders core sections", async () => {
    render(<App />);
    expect(await screen.findByText("Wardrobe Intelligence")).toBeTruthy();
    expect(screen.getByText(/Add Item/)).toBeTruthy();
    expect(screen.getByText(/Suggestions/)).toBeTruthy();
  });
});
