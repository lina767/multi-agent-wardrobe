import { MemoryRouter } from "react-router-dom";
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
  it("renders dashboard navigation", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard/profile"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Wardrobe Studio")).toBeTruthy();
    expect(screen.getByRole("link", { name: /1\. Identity/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /4\. Daily Edit/ })).toBeTruthy();
  });
});
