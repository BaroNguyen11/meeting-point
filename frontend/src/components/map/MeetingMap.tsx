"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  buildAnimatedRoutes,
  createGeoCircle,
  poisToGeoJson,
  ROUTE_PALETTE,
} from "@/lib/geo";
import {
  GeoJsonFeatureCollection,
  MapBounds,
  OptimumZone,
  Person,
  PoiItem,
} from "@/types/meeting";

maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");

interface MeetingMapProps {
  mapTheme: "dark" | "light";
  people: Person[];
  optimum?: OptimumZone;
  routes: GeoJsonFeatureCollection | null;
  topPois: PoiItem[];
  searchPins?: PoiItem[];
  selectedPoiId?: number | null;
  elapsedMinutes: number;
  focusTrigger: number;
  flyTarget: { lat: number; lng: number; zoom?: number; ts: number } | null;
  pickingMemberIdx: number | null;
  onMapPickLocation: (lat: number, lng: number) => void;
  onDragMember: (idx: number, lat: number, lng: number) => void;
  onSelectPoi: (poi: PoiItem) => void;
  onBoundsChange?: (bounds: MapBounds) => void;
}

export function MeetingMap({
  mapTheme,
  people,
  optimum,
  routes,
  topPois,
  searchPins = [],
  selectedPoiId,
  elapsedMinutes,
  focusTrigger,
  flyTarget,
  pickingMemberIdx,
  onMapPickLocation,
  onDragMember,
  onSelectPoi,
  onBoundsChange,
}: MeetingMapProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const personMarkersRef = useRef<maplibregl.Marker[]>([]);
  const searchMarkersRef = useRef<maplibregl.Marker[]>([]);
  const zoneCenterMarkerRef = useRef<maplibregl.Marker | null>(null);
  const topPoisRef = useRef<PoiItem[]>(topPois);
  const onSelectPoiRef = useRef(onSelectPoi);
  const onBoundsChangeRef = useRef(onBoundsChange);
  const pickingIdxRef = useRef<number | null>(pickingMemberIdx);
  const onMapPickRef = useRef(onMapPickLocation);

  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    topPoisRef.current = topPois;
    onSelectPoiRef.current = onSelectPoi;
    onBoundsChangeRef.current = onBoundsChange;
    pickingIdxRef.current = pickingMemberIdx;
    onMapPickRef.current = onMapPickLocation;
  });

  const setupMapLayers = useCallback((map: maplibregl.Map) => {
    // 1. Vùng bán kính 450m quanh tâm khu vực hẹn
    if (!map.getSource("zone-circle-src")) {
      map.addSource("zone-circle-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "zone-circle-fill",
        type: "fill",
        source: "zone-circle-src",
        paint: { "fill-color": "#0ea5e9", "fill-opacity": 0.1 },
      });
      map.addLayer({
        id: "zone-circle-outline",
        type: "line",
        source: "zone-circle-src",
        paint: {
          "line-color": "#38bdf8",
          "line-width": 1.5,
          "line-dasharray": [3, 2],
          "line-opacity": 0.8,
        },
      });
    }

    // 2. Đường dẫn nền mờ (hiển thị toàn bộ lộ trình dự kiến)
    if (!map.getSource("routes-base-src")) {
      map.addSource("routes-base-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "routes-base-layer",
        type: "line",
        source: "routes-base-src",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-width": 3,
          "line-opacity": 0.22,
          "line-color": [
            "match",
            ["get", "person_index"],
            0, ROUTE_PALETTE[0],
            1, ROUTE_PALETTE[1],
            2, ROUTE_PALETTE[2],
            3, ROUTE_PALETTE[3],
            4, ROUTE_PALETTE[4],
            5, ROUTE_PALETTE[5],
            "#0ea5e9",
          ],
        },
      });
    }

    // 3. Tuyến đường đang chạy (1 đường chạy sắc nét + đầu điểm sáng)
    if (!map.getSource("routes-active-src")) {
      map.addSource("routes-active-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "routes-active-casing",
        type: "line",
        source: "routes-active-src",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-width": 6.5, "line-color": "#09090b", "line-opacity": 0.7 },
      });
      map.addLayer({
        id: "routes-active-layer",
        type: "line",
        source: "routes-active-src",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-width": 4,
          "line-color": [
            "match",
            ["get", "person_index"],
            0, ROUTE_PALETTE[0],
            1, ROUTE_PALETTE[1],
            2, ROUTE_PALETTE[2],
            3, ROUTE_PALETTE[3],
            4, ROUTE_PALETTE[4],
            5, ROUTE_PALETTE[5],
            "#0ea5e9",
          ],
        },
      });
    }

    if (!map.getSource("routes-head-src")) {
      map.addSource("routes-head-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "routes-head-layer",
        type: "circle",
        source: "routes-head-src",
        paint: {
          "circle-radius": 5,
          "circle-color": "#ffffff",
          "circle-stroke-width": 2.5,
          "circle-stroke-color": [
            "match",
            ["get", "person_index"],
            0, ROUTE_PALETTE[0],
            1, ROUTE_PALETTE[1],
            2, ROUTE_PALETTE[2],
            3, ROUTE_PALETTE[3],
            4, ROUTE_PALETTE[4],
            5, ROUTE_PALETTE[5],
            "#0ea5e9",
          ],
        },
      });
    }

    // 4. Native WebGL Symbol Layer cho các quán (tự động chống đè nhãn theo mức zoom)
    if (!map.getSource("pois-src")) {
      map.addSource("pois-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "pois-circle",
        type: "circle",
        source: "pois-src",
        paint: {
          "circle-radius": ["case", ["==", ["get", "is_selected"], 1], 8, 5],
          "circle-color": ["case", ["==", ["get", "is_selected"], 1], "#f97316", "#f59e0b"],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#09090b",
        },
      });
      map.addLayer({
        id: "pois-label",
        type: "symbol",
        source: "pois-src",
        layout: {
          "text-field": ["get", "name"],
          "text-size": 11.5,
          "text-font": ["Open Sans Regular"],
          "text-variable-anchor": ["top", "bottom", "left", "right"],
          "text-radial-offset": 0.85,
          "text-justify": "auto",
          "text-allow-overlap": false,
          "text-optional": true,
        },
        paint: {
          "text-color": "#f4f4f5",
          "text-halo-color": "#09090b",
          "text-halo-width": 1.5,
        },
      });

      const handlePoiClick = (e: maplibregl.MapLayerMouseEvent) => {
        if (pickingIdxRef.current !== null) return;
        const feat = e.features?.[0];
        const poiId = feat?.properties?.poi_id;
        if (poiId === undefined) return;
        const found = topPoisRef.current.find((p) => p.poi_id === Number(poiId));
        if (found) onSelectPoiRef.current(found);
      };

      map.on("click", "pois-circle", handlePoiClick);
      map.on("click", "pois-label", handlePoiClick);
      map.on("mouseenter", "pois-circle", () => {
        if (pickingIdxRef.current === null) map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "pois-circle", () => {
        map.getCanvas().style.cursor = pickingIdxRef.current !== null ? "crosshair" : "";
      });
    }
  }, []);

  // Khởi tạo MapLibre lần đầu
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [106.699, 10.788],
      zoom: 13.5,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    const reportBounds = () => {
      if (!onBoundsChangeRef.current) return;
      const b = map.getBounds();
      const c = map.getCenter();
      onBoundsChangeRef.current({
        west: b.getWest(),
        south: b.getSouth(),
        east: b.getEast(),
        north: b.getNorth(),
        centerLat: c.lat,
        centerLng: c.lng,
      });
    };

    map.on("load", () => {
      setupMapLayers(map);
      setMapLoaded(true);
      reportBounds();
    });

    map.on("moveend", reportBounds);

    map.on("click", (e) => {
      if (pickingIdxRef.current !== null) {
        onMapPickRef.current(e.lngLat.lat, e.lngLat.lng);
      }
    });

    mapRef.current = map;
  }, [setupMapLayers]);

  // Con trỏ chuột khi bật chế độ chọn vị trí trên bản đồ
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = pickingMemberIdx !== null ? "crosshair" : "";
  }, [pickingMemberIdx]);

  // Chuyển đổi giao diện Sáng / Tối
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const styleUrl =
      mapTheme === "dark"
        ? "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        : "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json";

    map.setStyle(styleUrl);
    map.once("styledata", () => {
      setupMapLayers(map);
      if (routes) {
        (map.getSource("routes-base-src") as maplibregl.GeoJSONSource)?.setData(routes as any);
      }
      if (topPois.length > 0) {
        (map.getSource("pois-src") as maplibregl.GeoJSONSource)?.setData(
          poisToGeoJson(topPois, selectedPoiId) as any
        );
      }
      if (optimum) {
        (map.getSource("zone-circle-src") as maplibregl.GeoJSONSource)?.setData(
          createGeoCircle(optimum.lng, optimum.lat, 450) as any
        );
      }
      if (map.getLayer("pois-label")) {
        map.setPaintProperty("pois-label", "text-color", mapTheme === "dark" ? "#f4f4f5" : "#18181b");
        map.setPaintProperty("pois-label", "text-halo-color", mapTheme === "dark" ? "#09090b" : "#ffffff");
      }
    });
  }, [mapTheme]); // eslint-disable-line react-hooks/exhaustive-deps

  // Đồng bộ Tuyến đường nền & Tuyến đường đang chạy
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    if (!routes) {
      const empty = { type: "FeatureCollection", features: [] } as any;
      (map.getSource("routes-base-src") as maplibregl.GeoJSONSource)?.setData(empty);
      (map.getSource("routes-active-src") as maplibregl.GeoJSONSource)?.setData(empty);
      (map.getSource("routes-head-src") as maplibregl.GeoJSONSource)?.setData(empty);
      return;
    }

    (map.getSource("routes-base-src") as maplibregl.GeoJSONSource)?.setData(routes as any);
    const { activeLines, headPoints } = buildAnimatedRoutes(routes, elapsedMinutes);
    (map.getSource("routes-active-src") as maplibregl.GeoJSONSource)?.setData(activeLines as any);
    (map.getSource("routes-head-src") as maplibregl.GeoJSONSource)?.setData(headPoints as any);
  }, [routes, elapsedMinutes, mapLoaded]);

  // Đồng bộ POI Native Layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;
    (map.getSource("pois-src") as maplibregl.GeoJSONSource)?.setData(
      poisToGeoJson(topPois, selectedPoiId) as any
    );

    if (selectedPoiId) {
      const target =
        topPois.find((p) => p.poi_id === selectedPoiId) ||
        searchPins.find((p) => p.poi_id === selectedPoiId);
      if (target) {
        map.flyTo({
          center: [target.lng, target.lat],
          zoom: 15,
          duration: 650,
          padding: { left: 380, right: 400 },
        });
      }
    }
  }, [topPois, searchPins, selectedPoiId, mapLoaded]);

  // Ghim đỏ + Tên địa điểm khi tìm kiếm theo khu vực (giống Google Maps)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    searchMarkersRef.current.forEach((m) => m.remove());
    searchMarkersRef.current = searchPins.map((pin) => {
      const isSelected = pin.poi_id === selectedPoiId;
      const el = document.createElement("div");
      el.className = "cursor-pointer flex items-center gap-1.5 z-20 transition-transform hover:scale-105";
      el.innerHTML = `
        <span class="w-4 h-4 rounded-full ${
          isSelected ? "bg-sky-400 ring-4 ring-sky-400/30" : "bg-red-500 ring-2 ring-white"
        } shadow-lg flex items-center justify-center shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
        </span>
        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-md shadow-md whitespace-nowrap ${
          isSelected
            ? "bg-sky-500 text-zinc-950"
            : "bg-zinc-950/95 text-red-200 border border-red-500/50"
        }">
          ${pin.name}
        </span>
      `;
      el.onclick = (e) => {
        e.stopPropagation();
        onSelectPoiRef.current(pin);
      };
      return new maplibregl.Marker({ element: el, anchor: "left" })
        .setLngLat([pin.lng, pin.lat])
        .addTo(map);
    });
  }, [searchPins, selectedPoiId]);

  // Đồng bộ Vòng tròn 450m & Tâm khu vực
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    if (!optimum) {
      (map.getSource("zone-circle-src") as maplibregl.GeoJSONSource)?.setData({
        type: "FeatureCollection",
        features: [],
      } as any);
      if (zoneCenterMarkerRef.current) {
        zoneCenterMarkerRef.current.remove();
        zoneCenterMarkerRef.current = null;
      }
      return;
    }

    (map.getSource("zone-circle-src") as maplibregl.GeoJSONSource)?.setData(
      createGeoCircle(optimum.lng, optimum.lat, 450) as any
    );

    if (zoneCenterMarkerRef.current) zoneCenterMarkerRef.current.remove();
    const centerEl = document.createElement("div");
    centerEl.className = "pointer-events-none flex flex-col items-center z-30";
    centerEl.innerHTML = `
      <div class="px-2.5 py-1 rounded-md bg-sky-500 text-white text-[11px] font-bold shadow-lg border border-white/80 whitespace-nowrap mb-1">
        Tâm khu vực • ${optimum.f_max}p
      </div>
      <div class="relative flex items-center justify-center w-7 h-7">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-60"></span>
        <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-sky-500 border-2 border-white shadow"></span>
      </div>
    `;
    zoneCenterMarkerRef.current = new maplibregl.Marker({ element: centerEl })
      .setLngLat([optimum.lng, optimum.lat])
      .addTo(map);
  }, [optimum, mapLoaded]);

  // Bay tới điểm được tìm kiếm hoặc khu vực tối ưu
  useEffect(() => {
    if (!focusTrigger || !optimum || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [optimum.lng, optimum.lat],
      zoom: 14.3,
      duration: 650,
      padding: { left: 360, right: 0 },
    });
  }, [focusTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!flyTarget || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [flyTarget.lng, flyTarget.lat],
      zoom: flyTarget.zoom || 15.2,
      duration: 650,
      padding: { left: 360, right: 0 },
    });
  }, [flyTarget]);

  // Ghim thành viên có hiệu ứng sóng loang Radar Pulse đồng bộ màu từng người
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    personMarkersRef.current.forEach((m) => m.remove());
    personMarkersRef.current = people.map((p, idx) => {
      const color = ROUTE_PALETTE[idx % ROUTE_PALETTE.length];
      const el = document.createElement("div");
      el.className = "flex flex-col items-center cursor-grab z-20";
      el.innerHTML = `
        <div class="px-2.5 py-0.5 rounded-md bg-zinc-900/95 text-zinc-100 text-[11px] font-semibold shadow-md border border-zinc-700 flex items-center gap-1.5 mb-1">
          <span style="background:${color}" class="w-2 h-2 rounded-full"></span>
          <span>${p.name}</span>
        </div>
        <div class="relative flex items-center justify-center w-7 h-7">
          <span style="background:${color}" class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-55"></span>
          <span style="background:${color}" class="relative inline-flex rounded-full h-3.5 w-3.5 border-2 border-white shadow-md"></span>
        </div>
      `;
      const marker = new maplibregl.Marker({ element: el, draggable: true })
        .setLngLat([p.lng, p.lat])
        .addTo(map);

      marker.on("dragend", () => {
        const pos = marker.getLngLat();
        onDragMember(idx, pos.lat, pos.lng);
      });
      return marker;
    });
  }, [people]); // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={mapContainer} className="absolute inset-0 w-full h-full" />;
}