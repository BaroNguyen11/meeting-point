"use client";

import React, { useState } from "react";
import { Compass, Plus } from "lucide-react";
import { PoiDetailDrawer } from "@/components/drawer/PoiDetailDrawer";
import { MeetingMap } from "@/components/map/MeetingMap";
import { FilterBar } from "@/components/sidebar/FilterBar";
import { MemberList } from "@/components/sidebar/MemberList";
import { PoiList } from "@/components/sidebar/PoiList";
import { ZoneHeader } from "@/components/topbar/ZoneHeader";
import { useMeetingSolver } from "@/hooks/useMeetingSolver";
import { useRouteRunner } from "@/hooks/useWavefront";
import { MapBounds, PoiItem } from "@/types/meeting";

export default function MeetingPointApp() {
  const {
    people,
    setPeople,
    alpha,
    setAlpha,
    isRushHour,
    setIsRushHour,
    amenity,
    setAmenity,
    maxMinutes,
    solveData,
    activeRoutes,
    selectedPoi,
    poiEnrichment,
    isLoadingEnrichment,
    selectPoi,
    selectCustomPlace,
    clearSelectedPoi,
    handleDragMember,
    shareCurrentRoom,
  } = useMeetingSolver();

  const { elapsedMinutes, isRunning, replayRoute } = useRouteRunner(activeRoutes);
  const [mapTheme, setMapTheme] = useState<"dark" | "light">("dark");
  const [focusTrigger, setFocusTrigger] = useState<number>(0);
  const [pickingMemberIdx, setPickingMemberIdx] = useState<number | null>(null);
  const [flyTarget, setFlyTarget] = useState<{ lat: number; lng: number; zoom?: number; ts: number } | null>(null);
  const [mapBounds, setMapBounds] = useState<MapBounds | null>(null);
  const [searchPins, setSearchPins] = useState<PoiItem[]>([]);

  const addMember = () => {
    if (people.length >= 8) return;
    const nextNum = people.length + 1;
    setPeople((prev) => [
      ...prev,
      {
        id: `p_${Date.now()}`,
        name: `Bạn ${nextNum}`,
        address: "Nhà thờ Đức Bà, Quận 1",
        lat: 10.7798 + (Math.random() - 0.5) * 0.01,
        lng: 106.699 + (Math.random() - 0.5) * 0.01,
      },
    ]);
  };

  return (
    <div className="relative h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans select-none">
      <MeetingMap
        mapTheme={mapTheme}
        people={people}
        optimum={solveData?.optimum}
        routes={activeRoutes}
        topPois={solveData?.top_pois || []}
        searchPins={searchPins}
        selectedPoiId={selectedPoi?.poi_id}
        elapsedMinutes={elapsedMinutes}
        focusTrigger={focusTrigger}
        flyTarget={flyTarget}
        pickingMemberIdx={pickingMemberIdx}
        onMapPickLocation={(lat, lng) => {
          if (pickingMemberIdx === null) return;
          const targetIdx = pickingMemberIdx;
          setPickingMemberIdx(null);
          handleDragMember(targetIdx, lat, lng);
        }}
        onDragMember={handleDragMember}
        onSelectPoi={selectPoi}
        onBoundsChange={setMapBounds}
      />

      <ZoneHeader
        optimum={solveData?.optimum}
        people={people}
        mapBounds={mapBounds}
        searchPinsCount={searchPins.length}
        isRunning={isRunning}
        elapsedMinutes={elapsedMinutes}
        mapTheme={mapTheme}
        onFocusZone={() => {
          clearSelectedPoi();
          setFocusTrigger((n) => n + 1);
        }}
        onReplayRoute={replayRoute}
        onToggleTheme={() => setMapTheme((t) => (t === "dark" ? "light" : "dark"))}
        onShareRoom={shareCurrentRoom}
        onFlyToLocation={(lat, lng) => setFlyTarget({ lat, lng, zoom: 15.5, ts: Date.now() })}
        onAssignMemberLocation={(idx, sug) => {
          setPeople((prev) =>
            prev.map((p, i) =>
              i === idx ? { ...p, address: sug.label, lat: sug.lat, lng: sug.lng } : p
            )
          );
        }}
        onTestDestination={selectCustomPlace}
        onSetSearchPins={(pins) => setSearchPins(pins)}
        onClearSearchPins={() => setSearchPins([])}
      />

      <div className="absolute top-4 left-4 bottom-4 w-96.5 bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-md shadow-2xl z-20 flex flex-col overflow-hidden">
        <div className="px-4 py-3.5 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <Compass className="w-4 h-4 text-sky-400" />
              MeetPoint HCMC
            </h1>
            <p className="text-[11px] text-zinc-400 mt-0.5 tabular-nums">
              Định tuyến nhóm · {solveData?.compute_ms ?? "--"} ms
            </p>
          </div>
          <button
            onClick={addMember}
            disabled={people.length >= 8}
            className="px-2.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-medium flex items-center gap-1 disabled:opacity-40 transition"
          >
            <Plus className="w-3.5 h-3.5" /> Thêm người
          </button>
        </div>

        {people.length < 2 && (
          <div className="mx-3 mt-3 p-3 rounded-lg bg-zinc-800/70 border border-zinc-700/80 text-xs text-zinc-300 flex items-center justify-between gap-2">
            <span>
              {people.length === 0
                ? "Chưa có thành viên. Thêm ít nhất 2 người để tìm điểm hẹn."
                : "Thêm 1 người nữa để bắt đầu tính tuyến đường chung."}
            </span>
            <button
              onClick={addMember}
              className="px-2.5 py-1 rounded bg-sky-500 hover:bg-sky-400 text-zinc-950 font-semibold shrink-0 transition"
            >
              + Thêm
            </button>
          </div>
        )}

        <MemberList
          people={people}
          timesPerPerson={solveData?.times_per_person}
          pickingMemberIdx={pickingMemberIdx}
          onStartPickOnMap={setPickingMemberIdx}
          onChangePeople={setPeople}
        />

        <FilterBar
          amenity={amenity}
          alpha={alpha}
          maxMinutes={maxMinutes}
          isRushHour={isRushHour}
          onChangeAmenity={setAmenity}
          onChangeAlpha={setAlpha}
          onToggleRushHour={() => setIsRushHour((r) => !r)}
        />

        <PoiList
          pois={searchPins.length > 0 ? searchPins : solveData?.top_pois || []}
          selectedPoiId={selectedPoi?.poi_id}
          onSelectPoi={selectPoi}
        />
      </div>

      {selectedPoi && (
        <PoiDetailDrawer
          poi={selectedPoi}
          enrichment={poiEnrichment}
          isLoading={isLoadingEnrichment}
          onClose={clearSelectedPoi}
        />
      )}
    </div>
  );
}