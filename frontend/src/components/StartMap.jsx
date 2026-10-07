import React, { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";

export default function StartMap({
  runs = [],
  point,
  onChange,
  onSelect,
  focusId,
}) {
  const node = useRef(null),
    instance = useRef(null),
    layers = useRef(null),
    leaflet = useRef(null),
    fitted = useRef(false);
  const [ready, setReady] = useState(false),
    [error, setError] = useState("");
  const change = useRef(onChange),
    select = useRef(onSelect);
  change.current = onChange;
  select.current = onSelect;
  useEffect(() => {
    let cancelled = false,
      resize;
    import("leaflet")
      .then((module) => {
        if (cancelled) return;
        const L = module.default || module;
        leaflet.current = L;
        const map = L.map(node.current, { scrollWheelZoom: false }).setView(
          point ? [point.latitude, point.longitude] : [47.1, 8.3],
          point ? 14 : 8,
        );
        instance.current = map;
        L.tileLayer(
          import.meta.env.VITE_MAP_TILE_URL ||
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          {
            maxZoom: 19,
            attribution:
              import.meta.env.VITE_MAP_ATTRIBUTION ||
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          },
        )
          .addTo(map)
          .on("tileerror", () => {
            if (!cancelled)
              setError(
                "Einige Kartenausschnitte konnten nicht geladen werden. Bitte Internetverbindung prüfen.",
              );
          });
        layers.current = L.layerGroup().addTo(map);
        map.on("click", (event) => {
          const location = event.latlng.wrap();
          change.current?.({ latitude: location.lat, longitude: location.lng });
        });
        resize = new ResizeObserver(() => map.invalidateSize());
        resize.observe(node.current);
        setReady(true);
      })
      .catch(() => {
        if (!cancelled)
          setError(
            "Die Karte konnte nicht geladen werden. Bitte erneut laden.",
          );
      });
    return () => {
      cancelled = true;
      resize?.disconnect();
      instance.current?.remove();
      instance.current = null;
      setReady(false);
      fitted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!ready || !instance.current) return;
    const L = leaflet.current,
      layer = layers.current;
    layer.clearLayers();
    const icon = L.divIcon({
      className: "run-pin",
      html: '<span aria-hidden="true">●</span>',
      iconSize: [32, 40],
      iconAnchor: [16, 38],
    });
    runs.forEach((r) => {
      const label = document.createElement("span");
      label.textContent = `${r.distance_km} km · ${r.meeting_point}`;
      L.marker([r.latitude, r.longitude], {
        icon,
        title: `${r.distance_km} km · ${r.meeting_point}`,
        keyboard: true,
      })
        .addTo(layer)
        .bindTooltip(label)
        .on("click", () => select.current?.(r.id));
    });
    if (point)
      L.marker([point.latitude, point.longitude], {
        icon,
        title: "Gewählter Startpunkt",
      }).addTo(layer);
    if (!fitted.current && (runs.length || point)) {
      const coordinates = point
        ? [[point.latitude, point.longitude]]
        : runs.map((r) => [r.latitude, r.longitude]);
      instance.current.fitBounds(L.latLngBounds(coordinates), {
        padding: [36, 36],
        maxZoom: 14,
      });
      fitted.current = true;
    }
  }, [ready, runs, point]);
  useEffect(() => {
    const r = runs.find((r) => r.id === focusId);
    if (r && instance.current)
      instance.current.setView([r.latitude, r.longitude], 15);
  }, [focusId, ready]);
  function locate() {
    if (!navigator.geolocation) {
      setError("Dein Browser unterstützt keine Standortabfrage.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const value = {
          latitude: coords.latitude,
          longitude: coords.longitude,
        };
        instance.current?.setView([value.latitude, value.longitude], 15);
        change.current?.(value);
        setError("");
      },
      () =>
        setError(
          "Standort nicht verfügbar. Du kannst den Startpunkt direkt auf der Karte wählen.",
        ),
      { timeout: 10000 },
    );
  }
  return (
    <div className="map-wrap">
      <div
        className="map-canvas"
        ref={node}
        role="region"
        aria-label={
          onChange
            ? "Startpunkt auswählen: Karte mit Pfeiltasten verschieben oder einen Ort antippen"
            : "Karte der gemeinsamen Läufe"
        }
      />
      {!ready && !error && <span className="map-loading">Karte laden …</span>}
      {onChange && (
        <div className="map-actions">
          <button
            type="button"
            className="btn small"
            disabled={!ready}
            onClick={() => {
              const c = instance.current.getCenter().wrap();
              onChange({ latitude: c.lat, longitude: c.lng });
            }}
          >
            Kartenmitte als Startpunkt
          </button>
          <button type="button" className="text-button" onClick={locate}>
            Meinen Standort verwenden
          </button>
        </div>
      )}
      {error && (
        <p className="notice" role="status">
          {error}
        </p>
      )}
    </div>
  );
}
