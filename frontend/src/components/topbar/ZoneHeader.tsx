"use client";

import React, { useEffect, useState } from "react";
import {
  Check,
  MapPin,
  Moon,
  Navigation,
  Play,
  Radar,
  Search,
  Share2,
  Sun,
  Target,
  X,
} from "lucide-react";
import { fetchGeocode, searchPlacesInArea } from "@/lib/api";
import { GeoSuggestion, MapBounds, OptimumZone, Person, PoiItem } from "@/types/meeting";

interface ZoneHeaderProps {
  optimum?: OptimumZone;
  people: Person[];
  mapBounds: MapBounds | null;
  searchPinsCount: number;
  isRunning: boolean;
  elapsedMinutes: number;
  mapTheme: "dark" | "light";
  onFocusZone: () => void;
  onReplayRoute: () => void;
  onToggleTheme: () => void;
  onShareRoom: () => Promise<string>;
  onFlyToLocation: (lat: number, lng: number) => void;
  onAssignMemberLocation: (memberIdx: number, sug: GeoSuggestion) => void;
  onTestDestination: (sug: GeoSuggestion) => void;
  onSetSearchPins: (pins: PoiItem[], activeLabel: string) => void;
  onClearSearchPins: () => void;
}

const AREA_QUICK_CHIPS = [
  { label: "⚽ Sân bóng đá", query: "sân bóng đá" },
  { label: "☕ Cà phê", query: "cà phê" },
  { label: "🍜 Quán ăn", query: "quán ăn" },
  { label: "🎬 Giải trí", query: "giải trí" },
];

export function ZoneHeader({
  optimum,
  people,
  mapBounds,
  searchPinsCount,
  isRunning,
  elapsedMinutes,
  mapTheme,
  onFocusZone,
  onReplayRoute,
  onToggleTheme,
  onShareRoom,
  onFlyToLocation,
  onAssignMemberLocation,
  onTestDestination,
  onSetSearchPins,
  onClearSearchPins,
}: ZoneHeaderProps) {
  const [copied, setCopied] = useState(false);
  const [mapQuery, setMapQuery] = useState("");
  const [activeAreaQuery, setActiveAreaQuery] = useState<string | null>(null);
  const [mapResults, setMapResults] = useState<GeoSuggestion[]>([]);
  const [selectedPlace, setSelectedPlace] = useState<GeoSuggestion | null>(null);
  const [isSearchingArea, setIsSearchingArea] = useState(false);

  useEffect(() => {
    if (mapQuery.trim().length < 2) {
      setMapResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      const res = await fetchGeocode(
        mapQuery,
        mapBounds?.centerLat ?? 10.7769,
        mapBounds?.centerLng ?? 106.7009
      );
      setMapResults(res);
    }, 240);
    return () => clearTimeout(timer);
  }, [mapQuery, mapBounds?.centerLat, mapBounds?.centerLng]);

  const triggerAreaSearch = async (queryText: string) => {
    if (!queryText.trim()) return;
    const bounds = mapBounds ?? {
      west: 106.65,
      south: 10.74,
      east: 106.74,
      north: 10.82,
      centerLat: 10.7769,
      centerLng: 106.7009,
    };
    setIsSearchingArea(true);
    setActiveAreaQuery(queryText);
    setMapResults([]);
    setSelectedPlace(null);
    try {
      const places = await searchPlacesInArea({
        query: queryText,
        west: bounds.west,
        south: bounds.south,
        east: bounds.east,
        north: bounds.north,
      });
      onSetSearchPins(places, queryText);
    } finally {
      setIsSearchingArea(false);
    }
  };

  const handleCopyLink = async () => {
    await onShareRoom();
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="absolute top-4 left-[416px] right-4 z-20 flex flex-wrap items-start justify-between gap-2 pointer-events-none">
      {/* CỤM TRÁI: THÔNG TIN TÂM ĐIỂM HẸN */}
      <div className="flex flex-wrap items-center gap-2 pointer-events-auto">
        {optimum && (
          <div
            onClick={onFocusZone}
            className="cursor-pointer bg-zinc-900/95 hover:bg-zinc-800/95 backdrop-blur-md border border-zinc-700/90 rounded-md px-3.5 py-2 shadow-xl flex items-center gap-3 transition"
          >
            <div className="w-8 h-8 rounded-md bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0">
              <Target className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] text-zinc-400 font-medium flex items-center gap-2">
                <span>Khu vực đề xuất</span>
                <span className="text-zinc-600">•</span>
                <span className="text-zinc-300 font-mono tabular-nums">
                  Xa nhất {optimum?.f_max}p · Tổng {optimum?.f_sum}p
                </span>
              </div>
              <div className="text-xs font-semibold text-white mt-0.5 max-w-60 truncate">
                {optimum?.zone_name}
              </div>
            </div>
          </div>
        )}

        {optimum && (
          <button
            onClick={onReplayRoute}
            className="px-3 py-2.5 rounded-md bg-zinc-900/95 hover:bg-zinc-800 border border-zinc-700/90 text-xs font-medium text-zinc-200 shadow-xl flex items-center gap-1.5 transition tabular-nums"
          >
            <Play className="w-3.5 h-3.5 text-sky-400 fill-sky-400" />
            {isRunning ? `Đang chạy ${elapsedMinutes.toFixed(1)}p` : "Chạy lại"}
          </button>
        )}
        <button
          onClick={onToggleTheme}
          className="px-3 py-2.5 rounded-md bg-zinc-900/95 hover:bg-zinc-800 border border-zinc-700/90 text-xs font-medium text-zinc-300 shadow-xl flex items-center gap-1.5 transition"
        >
          {mapTheme === "dark" ? (
            <Sun className="w-3.5 h-3.5 text-amber-400" />
          ) : (
            <Moon className="w-3.5 h-3.5 text-sky-400" />
          )}
          {mapTheme === "dark" ? "Sáng" : "Tối"}
        </button>

        {optimum && (
          <button
            onClick={handleCopyLink}
            className={`px-3 py-2.5 rounded-md border text-xs font-medium shadow-xl flex items-center gap-1.5 transition ${copied
              ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
              : "bg-sky-500 hover:bg-sky-400 border-sky-400 text-zinc-950 font-semibold"
              }`}
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Share2 className="w-3.5 h-3.5" />}
            {copied ? "Đã chép" : "Chia sẻ"}
          </button>
        )}
      </div>

      {/* CỤM PHẢI: THANH TÌM KIẾM KIỂU GOOGLE MAPS + CHIPS KHU VỰC */}
      <div className="relative w-85 pointer-events-auto space-y-1.5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            triggerAreaSearch(mapQuery);
          }}
          className="bg-zinc-900/95 backdrop-blur-md border border-zinc-700/90 rounded-md px-3 py-2 shadow-xl flex items-center gap-2"
        >
          <Search className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
          <input
            value={mapQuery}
            onChange={(e) => {
              setMapQuery(e.target.value);
              setSelectedPlace(null);
            }}
            placeholder="Tìm địa chỉ, sân bóng đá, quán quanh đây..."
            className="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none"
          />
          {(mapQuery || searchPinsCount > 0) && (
            <button
              type="button"
              onClick={() => {
                setMapQuery("");
                setMapResults([]);
                setSelectedPlace(null);
                setActiveAreaQuery(null);
                onClearSearchPins();
              }}
              className="text-zinc-500 hover:text-zinc-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>

        {/* CHIPS TÌM NHANH THEO KHU VỰC ĐANG XEM (GIỐNG GOOGLE MAPS) */}
        <div className="flex flex-wrap items-center gap-1">
          {AREA_QUICK_CHIPS.map((chip) => {
            const isActive = activeAreaQuery === chip.query && searchPinsCount > 0;
            return (
              <button
                key={chip.query}
                type="button"
                onClick={() => {
                  setMapQuery(chip.query);
                  triggerAreaSearch(chip.query);
                }}
                className={`px-2 py-1 rounded-full text-[11px] font-medium backdrop-blur-md border shadow transition ${isActive
                  ? "bg-red-500 text-white border-red-400 font-semibold"
                  : "bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 border-zinc-700/80"
                  }`}
              >
                {chip.label}
              </button>
            );
          })}

          {activeAreaQuery && (
            <button
              type="button"
              onClick={() => triggerAreaSearch(activeAreaQuery)}
              className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 flex items-center gap-1"
            >
              <Radar className="w-3 h-3" />
              {isSearchingArea ? "Đang quét..." : `Quét lại vùng này (${searchPinsCount})`}
            </button>
          )}
        </div>

        {/* GỢI Ý AUTOCOMPLETE (ĐỊA CHỈ SỐ NHÀ + QUÉT TOÀN KHU VỰC) */}
        {mapResults.length > 0 && !selectedPlace && (
          <div className="bg-zinc-900/95 backdrop-blur-md border border-zinc-700 rounded-md shadow-2xl overflow-hidden">
            <button
              type="button"
              onClick={() => triggerAreaSearch(mapQuery)}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-red-300 bg-red-500/10 hover:bg-red-500/20 flex items-center gap-2 border-b border-zinc-800"
            >
              <Radar className="w-3.5 h-3.5 text-red-400 shrink-0" />
              <span>Hiện tất cả &quot;{mapQuery}&quot; trên vùng bản đồ này</span>
            </button>

            {mapResults.map((sug, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setSelectedPlace(sug);
                  setMapQuery(sug.label);
                  setMapResults([]);
                  onFlyToLocation(sug.lat, sug.lng);
                }}
                className="w-full text-left px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800 flex items-start gap-2 border-b border-zinc-800/80 last:border-none"
              >
                <MapPin className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                <span className="line-clamp-2">{sug.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* HỘP HÀNH ĐỘNG KHI CHỌN 1 ĐỊA CHỈ CỤ THỂ */}
        {selectedPlace && (
          <div className="bg-zinc-900/95 backdrop-blur-md border border-zinc-700 rounded-md p-3 shadow-2xl space-y-2.5">
            <div className="flex items-start justify-between gap-2">
              <div className="text-xs font-semibold text-white leading-snug line-clamp-2">
                {selectedPlace.label}
              </div>
              <button
                onClick={() => setSelectedPlace(null)}
                className="text-zinc-500 hover:text-zinc-200 shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              onClick={() => {
                onTestDestination(selectedPlace);
                setSelectedPlace(null);
              }}
              className="w-full py-1.5 px-2.5 rounded-md bg-sky-500 hover:bg-sky-400 text-zinc-950 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Navigation className="w-3.5 h-3.5" />
              Thử hẹn tại điểm này
            </button>

            <div>
              <div className="text-[10px] text-zinc-400 mb-1">Hoặc đặt làm điểm xuất phát của:</div>
              <div className="flex flex-wrap gap-1">
                {people.map((p, idx) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      onAssignMemberLocation(idx, selectedPlace);
                      setSelectedPlace(null);
                    }}
                    className="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-[11px] font-medium text-zinc-200 border border-zinc-700 transition"
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}