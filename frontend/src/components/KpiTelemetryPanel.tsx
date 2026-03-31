import { useEffect, useMemo, useState } from "react";

type TelemetryEvent = {
  name: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

type TelemetryCustomEvent = CustomEvent<TelemetryEvent>;

function asTelemetryEvent(value: unknown): TelemetryEvent | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const maybe = value as Partial<TelemetryEvent>;
  if (typeof maybe.name !== "string" || typeof maybe.timestamp !== "string") {
    return null;
  }
  return {
    name: maybe.name,
    timestamp: maybe.timestamp,
    payload: (maybe.payload as Record<string, unknown>) ?? {},
  };
}

export function KpiTelemetryPanel() {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);

  useEffect(() => {
    const existing = Array.isArray(window.__wardrobeTelemetry) ? window.__wardrobeTelemetry : [];
    setEvents(existing);

    const onTelemetry = (event: Event) => {
      const typed = event as TelemetryCustomEvent;
      const next = asTelemetryEvent(typed.detail);
      if (!next) {
        return;
      }
      setEvents((prev) => [...prev, next].slice(-20));
    };

    window.addEventListener("wardrobe-telemetry", onTelemetry);
    return () => {
      window.removeEventListener("wardrobe-telemetry", onTelemetry);
    };
  }, []);

  const eventCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const event of events) {
      counts.set(event.name, (counts.get(event.name) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [events]);

  return (
    <section className="card telemetryPanel">
      <div className="sectionHead">
        <p className="eyebrow">KPI Telemetry</p>
        <p className="metaNote">{events.length} recent events</p>
      </div>
      {eventCounts.length === 0 ? <p className="metaNote">No events yet. Interact with wardrobe and daily flows.</p> : null}
      {eventCounts.length > 0 ? (
        <div className="telemetryStats">
          {eventCounts.map(([name, count]) => (
            <span key={name} className="telemetryChip">
              {name}: {count}
            </span>
          ))}
        </div>
      ) : null}
      <div className="telemetryList">
        {events.slice().reverse().map((event, index) => (
          <article className="telemetryItem" key={`${event.timestamp}-${index}`}>
            <p>
              <strong>{event.name}</strong> at {new Date(event.timestamp).toLocaleTimeString()}
            </p>
            <p className="metaNote">{JSON.stringify(event.payload)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
