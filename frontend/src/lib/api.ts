import {
  GeoJsonFeatureCollection,
  GeoSuggestion,
  Person,
  PoiEnrichment,
  PoiItem,
  RoomPayload,
  SolveResponse,
} from "@/types/meeting";

const API_BASE = process.env.API_BASE || "http://127.0.0.1:8000";

async function requestJson<T>(url: string, init?: RequestInit, fallbackError = "Lỗi kết nối máy chủ"): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new Error("Không kết nối được Backend (127.0.0.1:8000). Hãy kiểm tra terminal chạy uvicorn.");
  }
  if (!res.ok) {
    throw new Error(fallbackError);
  }
  return res.json();
}

export async function fetchGeocode(
  query: string,
  centerLat = 10.7769,
  centerLng = 106.7009
): Promise<GeoSuggestion[]> {
  try {
    const qs = new URLSearchParams({
      q: query,
      lat: String(centerLat),
      lng: String(centerLng),
    });
    const res = await fetch(`${API_BASE}/api/geocode?${qs.toString()}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  } catch {
    return [];
  }
}

export async function searchPlacesInArea(params: {
  query: string;
  west: number;
  south: number;
  east: number;
  north: number;
}): Promise<PoiItem[]> {
  try {
    const qs = new URLSearchParams({
      q: params.query,
      west: String(params.west),
      south: String(params.south),
      east: String(params.east),
      north: String(params.north),
    });
    const res = await fetch(`${API_BASE}/api/search-area?${qs.toString()}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.places || [];
  } catch {
    return [];
  }
}

export async function fetchReverseGeocode(
  lat: number,
  lng: number,
): Promise<string> {
  try {
    const res = await fetch(
      `${API_BASE}/api/reverse-geocode?lat=${lat}&lng=${lng}`,
    );
    if (!res.ok) return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    const data = await res.json();
    return data.address || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  } catch {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
}

export async function solveMeetingPoint(params: {
  people: Person[];
  alpha: number;
  departHour: number | null;
  amenityFilter: string;
  maxMinutes: number;
}): Promise<SolveResponse> {
  return requestJson<SolveResponse>(
    `${API_BASE}/api/solve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        people: params.people.map(({ name, lat, lng }) => ({ name, lat, lng })),
        alpha: params.alpha,
        depart_hour: params.departHour,
        amenity_filter: params.amenityFilter,
        max_minutes: params.maxMinutes,
      }),
    },
    "Lỗi tính toán điểm hẹn",
  );
}

export async function fetchPoiRoutes(params: {
  people: Person[];
  poiId: number;
  departHour: number | null;
}): Promise<{ poi: PoiItem; routes: GeoJsonFeatureCollection }> {
  return requestJson<{ poi: PoiItem; routes: GeoJsonFeatureCollection }>(
    `${API_BASE}/api/poi-routes`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        people: params.people.map(({ name, lat, lng }) => ({ name, lat, lng })),
        poi_id: params.poiId,
        depart_hour: params.departHour,
      }),
    },
    "Lỗi tải tuyến đường tới địa điểm",
  );
}

export async function fetchCustomRoutes(params: {
  people: Person[];
  name: string;
  address: string;
  lat: number;
  lng: number;
  departHour: number | null;
}): Promise<{ poi: PoiItem; routes: GeoJsonFeatureCollection }> {
  return requestJson<{ poi: PoiItem; routes: GeoJsonFeatureCollection }>(
    `${API_BASE}/api/custom-route`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        people: params.people.map(({ name, lat, lng }) => ({ name, lat, lng })),
        name: params.name,
        address: params.address,
        lat: params.lat,
        lng: params.lng,
        depart_hour: params.departHour,
      }),
    },
    "Lỗi tải tuyến đường tới điểm tự chọn",
  );
}

export async function fetchPoiEnrichment(
  poiId: number,
): Promise<PoiEnrichment> {
  return requestJson<PoiEnrichment>(
    `${API_BASE}/api/pois/${poiId}/reviews`,
    undefined,
    "Lỗi tải dữ liệu đánh giá",
  );
}

export async function fetchCustomEnrichment(
  name: string,
  address: string,
  lat: number,
  lng: number,
): Promise<PoiEnrichment> {
  const qs = new URLSearchParams({
    name,
    address,
    lat: String(lat),
    lng: String(lng),
  });
  return requestJson<PoiEnrichment>(
    `${API_BASE}/api/custom-reviews?${qs.toString()}`,
    undefined,
    "Lỗi tải dữ liệu đánh giá",
  );
}

export async function createSharedRoom(payload: RoomPayload): Promise<string> {
  const data = await requestJson<{ room_id: string }>(
    `${API_BASE}/api/rooms`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể tạo link chia sẻ",
  );
  return data.room_id;
}

export async function loadSharedRoom(
  roomId: string,
): Promise<RoomPayload | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/rooms/${encodeURIComponent(roomId)}`,
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function attachTikTokLink(
  poiName: string,
  street: string,
  tiktokUrl: string,
): Promise<PoiEnrichment> {
  return requestJson<PoiEnrichment>(
    `${API_BASE}/api/attach-tiktok`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ poi_name: poiName, street, tiktok_url: tiktokUrl }),
    },
    "Không đọc được link TikTok này",
  );
}