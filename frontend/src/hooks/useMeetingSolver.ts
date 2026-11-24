import { useCallback, useEffect, useState } from "react";
import {
  createSharedRoom,
  fetchCustomEnrichment,
  fetchCustomRoutes,
  fetchPoiEnrichment,
  fetchPoiRoutes,
  fetchReverseGeocode,
  loadSharedRoom,
  solveMeetingPoint,
} from "@/lib/api";
import {
  GeoJsonFeatureCollection,
  GeoSuggestion,
  Person,
  PoiEnrichment,
  PoiItem,
  SolveResponse,
} from "@/types/meeting";

const INITIAL_PEOPLE: Person[] = [];

export function useMeetingSolver() {
  const [people, setPeople] = useState<Person[]>(INITIAL_PEOPLE);
  const [alpha, setAlpha] = useState<number>(0.5);
  const [isRushHour, setIsRushHour] = useState<boolean>(false);
  const [amenity, setAmenity] = useState<string>("all");
  const [maxMinutes, setMaxMinutes] = useState<number>(35);

  const [solveData, setSolveData] = useState<SolveResponse | null>(null);
  const [activeRoutes, setActiveRoutes] =
    useState<GeoJsonFeatureCollection | null>(null);
  const [selectedPoi, setSelectedPoi] = useState<PoiItem | null>(null);
  const [poiEnrichment, setPoiEnrichment] = useState<PoiEnrichment | null>(
    null,
  );
  const [isLoadingEnrichment, setIsLoadingEnrichment] =
    useState<boolean>(false);
  const [roomRestored, setRoomRestored] = useState<boolean>(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const roomId = params.get("room");
    if (!roomId) {
      setRoomRestored(true);
      return;
    }
    loadSharedRoom(roomId)
      .then((room) => {
        if (room) {
          setPeople(room.people);
          setAlpha(room.alpha);
          setIsRushHour(room.is_rush_hour);
          setAmenity(room.amenity_filter);
          setMaxMinutes(room.max_minutes);
        }
      })
      .finally(() => setRoomRestored(true));
  }, []);

  const runSolve = useCallback(async () => {
    if (!roomRestored) return;
    if (people.length < 2) {
      setSolveData(null);
      setActiveRoutes(null);
      setSelectedPoi(null);
      return;
    }
    try {
      const resSolve = await solveMeetingPoint({
        people,
        alpha,
        departHour: isRushHour ? 17.5 : null,
        amenityFilter: amenity,
        maxMinutes,
      });
      setSolveData(resSolve);
      setActiveRoutes(resSolve.routes);
      setSelectedPoi(null);
      setPoiEnrichment(null);
    } catch (err) {
      console.error("Lỗi khi giải bài toán điểm hẹn:", err);
    }
  }, [people, alpha, isRushHour, amenity, maxMinutes, roomRestored]);

  useEffect(() => {
    runSolve();
  }, [runSolve]);

  const selectPoi = useCallback(
    async (poi: PoiItem) => {
      setSelectedPoi(poi);
      setPoiEnrichment(null);
      setIsLoadingEnrichment(true);

      try {
        if (poi.poi_id < 0) {
          const [routeRes, enrichRes] = await Promise.all([
            fetchCustomRoutes({
              people,
              name: poi.name,
              address: poi.address,
              lat: poi.lat,
              lng: poi.lng,
              departHour: isRushHour ? 17.5 : null,
            }),
            fetchCustomEnrichment(poi.name, poi.address, poi.lat, poi.lng),
          ]);
          setSelectedPoi(routeRes.poi);
          setActiveRoutes(routeRes.routes);
          setPoiEnrichment(enrichRes);
          return;
        }

        const [routeRes, enrichRes] = await Promise.all([
          fetchPoiRoutes({
            people,
            poiId: poi.poi_id,
            departHour: isRushHour ? 17.5 : null,
          }),
          fetchPoiEnrichment(poi.poi_id),
        ]);
        setSelectedPoi(routeRes.poi);
        setActiveRoutes(routeRes.routes);
        setPoiEnrichment(enrichRes);
      } catch (err) {
        console.error("Lỗi tải chi tiết địa điểm:", err);
      } finally {
        setIsLoadingEnrichment(false);
      }
    },
    [people, isRushHour],
  );
  const selectCustomPlace = useCallback(
    async (sug: GeoSuggestion) => {
      if (sug.poi_id !== undefined) {
        const existing = solveData?.top_pois?.find(
          (p) => p.poi_id === sug.poi_id,
        );
        if (existing) {
          await selectPoi(existing);
          return;
        }
        await selectPoi({
          poi_id: sug.poi_id,
          name: sug.label.split(" · ")[0],
          amenity: "cafe",
          street: "",
          address: sug.label,
          lat: sug.lat,
          lng: sug.lng,
          f_sum: 0,
          f_max: 0,
          person_times: [],
        });
        return;
      }

      const parts = sug.label.split(",");
      const placeName = parts[0]?.trim() || sug.label;
      setIsLoadingEnrichment(true);
      setPoiEnrichment(null);

      try {
        const [routeRes, enrichRes] = await Promise.all([
          fetchCustomRoutes({
            people,
            name: placeName,
            address: sug.label,
            lat: sug.lat,
            lng: sug.lng,
            departHour: isRushHour ? 17.5 : null,
          }),
          fetchCustomEnrichment(placeName, sug.label, sug.lat, sug.lng),
        ]);
        setSelectedPoi(routeRes.poi);
        setActiveRoutes(routeRes.routes);
        setPoiEnrichment(enrichRes);
      } catch (err) {
        console.error("Lỗi định tuyến tới địa điểm tự chọn:", err);
      } finally {
        setIsLoadingEnrichment(false);
      }
    },
    [people, isRushHour, solveData, selectPoi],
  );

  const clearSelectedPoi = () => {
    setSelectedPoi(null);
    setPoiEnrichment(null);
    if (solveData?.routes) {
      setActiveRoutes(solveData.routes);
    }
  };

  const handleDragMember = async (idx: number, lat: number, lng: number) => {
    setPeople((prev) =>
      prev.map((p, i) =>
        i === idx ? { ...p, lat, lng, address: "Đang xác định đường..." } : p,
      ),
    );
    const resolvedAddress = await fetchReverseGeocode(lat, lng);
    setPeople((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, address: resolvedAddress } : p)),
    );
  };

  const shareCurrentRoom = async (): Promise<string> => {
    const roomId = await createSharedRoom({
      people,
      alpha,
      is_rush_hour: isRushHour,
      amenity_filter: amenity,
      max_minutes: maxMinutes,
      selected_poi_id:
        selectedPoi && selectedPoi.poi_id >= 0 ? selectedPoi.poi_id : null,
    });
    const shareUrl = `${window.location.origin}${window.location.pathname}?room=${roomId}`;
    window.history.replaceState({}, "", `?room=${roomId}`);
    await navigator.clipboard.writeText(shareUrl);
    return shareUrl;
  };

  return {
    people,
    setPeople,
    alpha,
    setAlpha,
    isRushHour,
    setIsRushHour,
    amenity,
    setAmenity,
    maxMinutes,
    setMaxMinutes,
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
  };
}
