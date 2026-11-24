import { GeoJsonFeatureCollection, PoiItem } from "@/types/meeting";

export const ROUTE_PALETTE = [
  "#0ea5e9", // Sky
  "#f43f5e", // Rose
  "#f59e0b", // Amber
  "#10b981", // Emerald
  "#8b5cf6", // Violet
  "#ec4899", // Pink
  "#14b8a6", // Teal
  "#f97316", // Orange
];

export function createGeoCircle(
  lng: number,
  lat: number,
  radiusMeters: number,
  points = 64
): GeoJsonFeatureCollection {
  const coords: [number, number][] = [];
  const distanceX = radiusMeters / (111320 * Math.cos((lat * Math.PI) / 180));
  const distanceY = radiusMeters / 110574;

  for (let i = 0; i < points; i++) {
    const theta = (i / points) * (2 * Math.PI);
    coords.push([lng + distanceX * Math.cos(theta), lat + distanceY * Math.sin(theta)]);
  }
  coords.push(coords[0]);

  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [coords] },
      },
    ],
  };
}

export function poisToGeoJson(pois: PoiItem[], selectedPoiId?: number | null): GeoJsonFeatureCollection {
  return {
    type: "FeatureCollection",
    features: pois.map((poi, idx) => ({
      type: "Feature",
      properties: {
        poi_id: poi.poi_id,
        name: poi.name,
        amenity: poi.amenity,
        f_max: poi.f_max,
        rank: idx + 1,
        is_selected: poi.poi_id === selectedPoiId ? 1 : 0,
      },
      geometry: {
        type: "Point",
        coordinates: [poi.lng, poi.lat],
      },
    })),
  };
}

/**
 * Cắt từng tuyến đường theo mốc thời gian chạy hiện tại (elapsedMinutes)
 * Trả về cả đường đã chạy (activeLines) và tọa độ đầu mũi tên đang chạy (headPoints).
 */
export function buildAnimatedRoutes(
  routes: GeoJsonFeatureCollection | null,
  elapsedMinutes: number
): { activeLines: GeoJsonFeatureCollection; headPoints: GeoJsonFeatureCollection } {
  if (!routes || !routes.features.length) {
    return {
      activeLines: { type: "FeatureCollection", features: [] },
      headPoints: { type: "FeatureCollection", features: [] },
    };
  }

  const activeFeatures: any[] = [];
  const headFeatures: any[] = [];

  for (const feat of routes.features) {
    const coords: [number, number][] = feat.geometry?.coordinates || [];
    if (coords.length < 2) continue;

    const totalMin = Math.max(Number(feat.properties?.minutes || 1), 0.1);
    const ratio = Math.min(1, Math.max(0, elapsedMinutes / totalMin));

    // Tính tổng độ dài hình học của tuyến để nội suy mượt từng đoạn
    const segLens: number[] = [];
    let totalLen = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const dx = coords[i + 1][0] - coords[i][0];
      const dy = coords[i + 1][1] - coords[i][1];
      const d = Math.hypot(dx, dy);
      segLens.push(d);
      totalLen += d;
    }

    const targetLen = totalLen * ratio;
    const slicedCoords: [number, number][] = [coords[0]];
    let accLen = 0;
    let headCoord: [number, number] = coords[0];

    for (let i = 0; i < segLens.length; i++) {
      const seg = segLens[i];
      if (accLen + seg <= targetLen) {
        slicedCoords.push(coords[i + 1]);
        headCoord = coords[i + 1];
        accLen += seg;
      } else {
        const remain = targetLen - accLen;
        const t = seg > 0 ? remain / seg : 0;
        const interp: [number, number] = [
          coords[i][0] + (coords[i + 1][0] - coords[i][0]) * t,
          coords[i][1] + (coords[i + 1][1] - coords[i][1]) * t,
        ];
        slicedCoords.push(interp);
        headCoord = interp;
        break;
      }
    }

    activeFeatures.push({
      type: "Feature",
      properties: feat.properties,
      geometry: { type: "LineString", coordinates: slicedCoords },
    });

    headFeatures.push({
      type: "Feature",
      properties: feat.properties,
      geometry: { type: "Point", coordinates: headCoord },
    });
  }

  return {
    activeLines: { type: "FeatureCollection", features: activeFeatures },
    headPoints: { type: "FeatureCollection", features: headFeatures },
  };
}