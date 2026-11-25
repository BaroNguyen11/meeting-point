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
  const [isMobileExpanded, setIsMobileExpanded] = useState<boolean>(true);

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

  const handleSelectPoiAndCollapse = (poi: PoiItem) => {
    selectPoi(poi);
    setIsMobileExpanded(false);
  };

  const handleReplayAndCollapse = () => {
    replayRoute();
    setIsMobileExpanded(false);
  };

  return (
    <div className="relative h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans select-none">
      {/* Lớp bản đồ: z-0 để không đè lên UI */}
      <div className="relative z-0 w-full h-full">
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
        onSelectPoi={handleSelectPoiAndCollapse}
        onBoundsChange={setMapBounds}
      />
      </div>{/* end z-0 map wrapper */}

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
        onReplayRoute={handleReplayAndCollapse}
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
        onTestDestination={(sug) => {
          selectCustomPlace(sug);
          setIsMobileExpanded(false);
        }}
        onSetSearchPins={(pins) => setSearchPins(pins)}
        onClearSearchPins={() => setSearchPins([])}
      />

      {/* Sidebar / Bottom Sheet: z-30 để nổi trên bản đồ */}
      <div
        className={`absolute top-4 left-4 bottom-4 w-[384px] bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-md shadow-2xl z-30 flex flex-col md:overflow-hidden max-md:top-auto max-md:left-0 max-md:right-0 max-md:bottom-0 max-md:w-full max-md:rounded-t-2xl max-md:rounded-b-none max-md:border-x-0 max-md:border-b-0 max-md:border-t max-md:overflow-y-auto ${
          isMobileExpanded ? "max-md:h-[62vh]" : "max-md:h-16"
        } transition-[height] duration-250 ease-out`}
      >
        {/* Mobile Drag Handle */}
        <div
          onClick={() => setIsMobileExpanded((v) => !v)}
          className="md:hidden w-full flex flex-col items-center pt-2.5 pb-1 cursor-pointer select-none touch-none hover:bg-zinc-800/40 transition-colors shrink-0"
        >
          <div className="w-10 h-1 rounded-full bg-zinc-600" />
        </div>

        <div className="px-4 py-3 md:py-3.5 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <div
            className="cursor-pointer md:cursor-default flex-1 min-w-0 pr-2"
            onClick={() => setIsMobileExpanded((v) => !v)}
          >
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-sky-400 shrink-0" />
              <h1 className="text-sm font-bold text-white tracking-tight truncate">
                MeetPoint HCMC
              </h1>
              {/* Nút bấm chuyển 2 mức chiều cao chỉ hiện trên mobile */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsMobileExpanded((v) => !v);
                }}
                className="md:hidden ml-auto px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-800 hover:bg-zinc-700 text-sky-400 border border-zinc-700 transition shrink-0 whitespace-nowrap"
              >
                {isMobileExpanded ? "Thu gọn ▾" : "Mở rộng ▴"}              </button>
            </div>
            <p className="text-[11px] text-zinc-400 mt-0.5 tabular-nums truncate">
              {people.length > 0 ? `${people.length} thành viên` : "Chưa có thành viên"} · {solveData?.compute_ms ? `${solveData.compute_ms} ms` : "Đang chờ"}
            </p>
          </div>
          <button
            onClick={addMember}
            disabled={people.length >= 8}
            className="px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-medium flex items-center gap-1 disabled:opacity-40 transition shrink-0 whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Thêm người</span>
          </button>
        </div>

        {people.length < 2 && (
          <div className="mx-3 mt-3 p-3 rounded-md bg-zinc-800/70 border border-zinc-700/80 text-xs text-zinc-300 flex items-center justify-between gap-2">
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

        {/* Body: PC = flex col scroll riêng từng vùng; Mobile = block cuộn toàn bộ */}
        <div className="md:flex md:flex-col md:flex-1 md:min-h-0 md:overflow-hidden max-md:block">
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
          onSelectPoi={handleSelectPoiAndCollapse}
        />
        </div>
      </div>

      {/* PoiDetailDrawer: z-50 nổi trên tất cả */}
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