"use client";

import React from "react";
import { Clock, Coffee, Compass, SlidersHorizontal, Trophy, Utensils } from "lucide-react";

interface FilterBarProps {
  amenity: string;
  alpha: number;
  maxMinutes: number;
  isRushHour: boolean;
  onChangeAmenity: (val: string) => void;
  onChangeAlpha: (val: number) => void;
  onToggleRushHour: () => void;
}

const FILTER_TABS = [
  { id: "all", label: "Tất cả", icon: null },
  { id: "cafe", label: "Cà phê", icon: Coffee },
  { id: "restaurant", label: "Quán ăn", icon: Utensils },
  { id: "sports", label: "Sân bóng", icon: Trophy },
  { id: "entertainment", label: "Giải trí", icon: Compass },
];

export function FilterBar({
  amenity,
  alpha,
  maxMinutes,
  isRushHour,
  onChangeAmenity,
  onChangeAlpha,
  onToggleRushHour,
}: FilterBarProps) {
  return (
    <div className="p-3 border-b border-zinc-800 bg-zinc-950/40 space-y-2.5">
      <div className="flex flex-wrap gap-1.5">
        {FILTER_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = amenity === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onChangeAmenity(tab.id)}
              className={`py-1.5 px-2.5 rounded-lg text-[11px] font-medium flex items-center gap-1 transition ${
                active
                  ? "bg-white text-zinc-950 font-semibold shadow-sm"
                  : "bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-zinc-800"
              }`}
            >
              {Icon && <Icon className="w-3 h-3" />}
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-xs gap-3">
        <div className="flex-1">
          <div className="flex justify-between text-[11px] text-zinc-400 mb-1 tabular-nums">
            <span className="flex items-center gap-1">
              <SlidersHorizontal className="w-3 h-3" /> Độ công bằng (α = {alpha})
            </span>
            <span>≤ {maxMinutes}p</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={alpha}
            onChange={(e) => onChangeAlpha(parseFloat(e.target.value))}
            className="w-full accent-sky-400 h-1 bg-zinc-800 rounded-lg cursor-pointer"
          />
        </div>

        <button
          onClick={onToggleRushHour}
          className={`px-2.5 py-1.5 rounded-lg text-[11px] font-medium border shrink-0 flex items-center gap-1.5 transition ${
            isRushHour
              ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
              : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200"
          }`}
        >
          <Clock className="w-3 h-3" />
          {isRushHour ? "17:30 Cao điểm" : "Giờ thường"}
        </button>
      </div>
    </div>
  );
}