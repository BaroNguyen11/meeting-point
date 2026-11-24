export interface Person {
  id: string;
  name: string;
  address: string;
  lat: number;
  lng: number;
}

export interface GeoSuggestion {
  label: string;
  lat: number;
  lng: number;
  poi_id?: number;
}
export interface PersonTime {
  name: string;
  minutes: number;
  km?: number;
  snapped_coord?: [number, number];
}

export interface OptimumZone {
  node_idx: number;
  zone_name: string;
  lat: number;
  lng: number;
  f_sum: number;
  f_max: number;
}

export interface PoiItem {
  poi_id: number;
  name: string;
  amenity: string;
  category?: string;
  sub_type?: string;
  street: string;
  address: string;
  opening_hours?: string | null;
  cuisine?: string | null;
  lat: number;
  lng: number;
  f_sum: number;
  f_max: number;
  score?: number;
  person_times: PersonTime[];
}

export interface GeoJsonFeature {
  type: "Feature";
  properties: Record<string, any>;
  geometry: {
    type: string;
    coordinates: any;
  };
}

export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
}

export interface SolveResponse {
  compute_ms: number;
  optimum: OptimumZone;
  times_per_person: PersonTime[];
  routes: GeoJsonFeatureCollection;
  top_pois: PoiItem[];
}

export interface KolVideo {
  platform?: "tiktok" | "youtube";
  video_id: string;
  title: string;
  channel_title: string;
  published_at: string;
  thumbnail: string;
  url: string;
  embed_url?: string;
}

export interface PoiEnrichment {
  rating: number | null;
  review_count: number | null;
  price_level: string | null;
  photo_url: string | null;
  highlights?: string[];
  review_snippets?: string[];
  kol_videos: KolVideo[];
  search_links?: {
    tiktok: string;
    youtube: string;
    google_maps: string;
  };
}

export interface RoomPayload {
  people: Person[];
  alpha: number;
  is_rush_hour: boolean;
  amenity_filter: string;
  max_minutes: number;
  selected_poi_id?: number | null;
}

export interface MapBounds {
  west: number;
  south: number;
  east: number;
  north: number;
  centerLat: number;
  centerLng: number;
}

export interface GeoSuggestion {
  label: string;
  lat: number;
  lng: number;
  poi_id?: number;
  category?: string;
}