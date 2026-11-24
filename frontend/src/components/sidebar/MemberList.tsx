"use client";

import React, { useEffect, useState } from "react";
import { Crosshair, MapPin, Search, Trash2 } from "lucide-react";
import { fetchGeocode } from "@/lib/api";
import { ROUTE_PALETTE } from "@/lib/geo";
import { GeoSuggestion, Person, PersonTime } from "@/types/meeting";

interface MemberListProps {
  people: Person[];
  timesPerPerson?: PersonTime[];
  pickingMemberIdx: number | null;
  onStartPickOnMap: (idx: number | null) => void;
  onChangePeople: React.Dispatch<React.SetStateAction<Person[]>>;
}

export function MemberList({
  people,
  timesPerPerson,
  pickingMemberIdx,
  onStartPickOnMap,
  onChangePeople,
}: MemberListProps) {
  const [activeSearchIdx, setActiveSearchIdx] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [suggestions, setSuggestions] = useState<GeoSuggestion[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  useEffect(() => {
    if (activeSearchIdx === null || searchQuery.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      const res = await fetchGeocode(searchQuery);
      setSuggestions(res);
      setIsSearching(false);
    }, 260);
    return () => clearTimeout(timer);
  }, [searchQuery, activeSearchIdx]);

  const removeMember = (idx: number) => {
    if (people.length <= 2) return;
    onChangePeople((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div className="p-3 border-b border-zinc-800 space-y-2 max-h-61.25 overflow-y-auto">
      {pickingMemberIdx !== null && (
        <div className="px-2.5 py-1.5 rounded-lg bg-sky-500/15 border border-sky-500/40 text-[11px] text-sky-300 flex items-center justify-between">
          <span>Click lên bản đồ để đặt vị trí cho {people[pickingMemberIdx]?.name}</span>
          <button
            onClick={() => onStartPickOnMap(null)}
            className="text-zinc-300 hover:text-white underline ml-2"
          >
            Hủy
          </button>
        </div>
      )}

      {people.map((person, idx) => {
        const personTime = timesPerPerson?.[idx]?.minutes;
        const color = ROUTE_PALETTE[idx % ROUTE_PALETTE.length];
        const isPicking = pickingMemberIdx === idx;

        return (
          <div
            key={person.id}
            className={`relative bg-zinc-950/80 border rounded-lg p-2 transition ${
              isPicking ? "border-sky-500" : "border-zinc-800/90"
            }`}
          >
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
              <input
                value={person.name}
                onChange={(e) =>
                  onChangePeople((prev) =>
                    prev.map((p, i) => (i === idx ? { ...p, name: e.target.value } : p))
                  )
                }
                className="w-12 bg-transparent text-xs font-semibold text-white focus:outline-none border-b border-transparent focus:border-sky-400"
              />
              <div className="flex-1 relative flex items-center">
                <Search className="w-3 h-3 text-zinc-500 absolute left-2 pointer-events-none" />
                <input
                  value={activeSearchIdx === idx ? searchQuery : person.address}
                  onFocus={() => {
                    setActiveSearchIdx(idx);
                    setSearchQuery(person.address);
                  }}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Nhập địa chỉ, quán..."
                  className="w-full bg-zinc-900 text-xs text-zinc-200 pl-6 pr-2 py-1 rounded-md border border-zinc-800 focus:border-sky-500 focus:outline-none"
                />
              </div>
              <button
                title="Chọn điểm trên bản đồ"
                onClick={() => onStartPickOnMap(isPicking ? null : idx)}
                className={`p-1 rounded border transition ${
                  isPicking
                    ? "bg-sky-500 text-zinc-950 border-sky-400"
                    : "bg-zinc-900 text-zinc-400 hover:text-white border-zinc-800"
                }`}
              >
                <Crosshair className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-mono text-zinc-300 shrink-0 w-9 text-right tabular-nums">
                {personTime !== undefined ? `${personTime}p` : "--"}
              </span>
              {people.length > 2 && (
                <button onClick={() => removeMember(idx)} className="text-zinc-500 hover:text-rose-400 p-0.5">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {activeSearchIdx === idx && (suggestions.length > 0 || isSearching) && (
              <div className="mt-1.5 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl overflow-hidden z-30">
                {isSearching && (
                  <div className="px-3 py-2 text-[11px] text-zinc-400">Đang tìm địa chỉ...</div>
                )}
                {suggestions.map((sug, sIdx) => (
                  <button
                    key={sIdx}
                    onClick={() => {
                      onChangePeople((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, address: sug.label, lat: sug.lat, lng: sug.lng } : p
                        )
                      );
                      setActiveSearchIdx(null);
                      setSuggestions([]);
                    }}
                    className="w-full text-left px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800 flex items-start gap-2 border-b border-zinc-800/70 last:border-none"
                  >
                    <MapPin className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                    <span className="line-clamp-2">{sug.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}