"use client";

import React from "react";
import { PoiItem } from "@/types/meeting";

interface PoiListProps {
  pois: PoiItem[];
  selectedPoiId?: number | null;
  onSelectPoi: (poi: PoiItem) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  cafe: "Cà phê",
  restaurant: "Quán ăn",
  sports: "Thể thao",
  entertainment: "Giải trí",
};

export function PoiList({ pois, selectedPoiId, onSelectPoi }: PoiListProps) {
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      <div className="text-[11px] font-medium text-zinc-400 px-1 flex justify-between">
        <span>Địa điểm phù hợp nhất</span>
        <span className="tabular-nums">{pois.length} kết quả</span>
      </div>

      {pois.map((poi, idx) => {
        const isSelected = selectedPoiId === poi.poi_id;
        const badge = CATEGORY_LABELS[poi.category || poi.amenity] || "Địa điểm";

        return (
          <div
            key={poi.poi_id}
            onClick={() => onSelectPoi(poi)}
            className={`p-3 rounded-md border cursor-pointer transition ${
              isSelected
                ? "bg-zinc-800/90 border-sky-500/70"
                : "bg-zinc-950/60 border-zinc-800/90 hover:border-zinc-700 hover:bg-zinc-900"
            }`}
          >
            <div className="flex justify-between items-start gap-2">
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-zinc-500">
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <h3 className="text-sm font-semibold text-zinc-100 leading-tight">{poi.name}</h3>
                </div>
                <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">{poi.address}</p>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 shrink-0">
                {badge}
              </span>
            </div>

            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px] tabular-nums">
              <span className="text-zinc-300">
                Xa nhất: <strong className="text-white font-semibold">{poi.f_max} phút</strong>
              </span>
              <span className="text-zinc-500">Tổng {poi.f_sum}p</span>
              <span className="text-sky-400 font-medium">Chi tiết & Review →</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}