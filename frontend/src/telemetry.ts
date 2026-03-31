type EventPayload = Record<string, string | number | boolean | null | undefined>;

interface TelemetryEvent {
  name: string;
  timestamp: string;
  payload: EventPayload;
}

declare global {
  interface Window {
    __wardrobeTelemetry?: TelemetryEvent[];
  }
}

export function trackEvent(name: string, payload: EventPayload = {}) {
  const event: TelemetryEvent = {
    name,
    timestamp: new Date().toISOString(),
    payload,
  };

  window.__wardrobeTelemetry = window.__wardrobeTelemetry ?? [];
  window.__wardrobeTelemetry.push(event);
  window.dispatchEvent(new CustomEvent("wardrobe-telemetry", { detail: event }));
  console.info("[telemetry]", event);
}
