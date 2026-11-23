"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Play, Pause, RotateCcw, Clock, Users, Coffee, Navigation, Sliders } from "lucide-react";
maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
const API_BASE = "http://127.0.0.1:8000";

const PERSON_COLORS = ["#00f5d4", "#ff006e", "#ffbe0b", "#8338ec", "#3a86ff", "#fb5607"];

interface Person {
  name: string;
  lat: number;
  lng: number;
}

const INITIAL_PEOPLE: Person[] = [
  { name: "An (Bến Thành)", lat: 10.7725, lng: 106.6980 },
  { name: "Bình (Hồ Con Rùa)", lat: 10.7827, lng: 106.6959 },
  { name: "Chi (Hàng Xanh)", lat: 10.8013, lng: 106.7114 },
  { name: "Phi (Vạn Kiếp)", lat: 10.7995, lng: 106.6922 },
];

export default function MeetingPointApp() {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const optMarkerRef = useRef<maplibregl.Marker | null>(null);
  const poiMarkerRef = useRef<maplibregl.Marker | null>(null);

  const [people, setPeople] = useState<Person[]>(INITIAL_PEOPLE);
  const [alpha, setAlpha] = useState<number>(0.5);
  const [isRushHour, setIsRushHour] = useState<boolean>(false);
  const [amenity, setAmenity] = useState<string>("cafe");

  const [solveData, setSolveData] = useState<any>(null);
  const [wavefrontData, setWavefrontData] = useState<any>(null);
  const [selectedPoi, setSelectedPoi] = useState<any>(null);

  // State điều khiển Animation Nước Loang
  const [currentTime, setCurrentTime] = useState<number>(15);
  const [maxWaveTime, setMaxWaveTime] = useState<number>(15);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // 1. Khởi tạo bản đồ MapLibre Dark Mode
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [106.699, 10.788],
      zoom: 13.5,
    });

    map.on("load", () => {
      // Nguồn dữ liệu các nhánh đường nước loang (Wavefront)
      map.addSource("wavefront-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "wavefront-layer",
        type: "line",
        source: "wavefront-src",
        paint: {
          "line-width": 2.2,
          "line-opacity": 0.75,
          "line-color": [
            "match",
            ["get", "person"],
            0, PERSON_COLORS[0],
            1, PERSON_COLORS[1],
            2, PERSON_COLORS[2],
            3, PERSON_COLORS[3],
            "#ffffff",
          ],
        },
      });

      // Nguồn dữ liệu tuyến đường ngắn nhất chốt hạ (Routes)
      map.addSource("routes-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "routes-glow",
        type: "line",
        source: "routes-src",
        paint: {
          "line-width": 8,
          "line-blur": 6,
          "line-opacity": 0.45,
          "line-color": [
            "match",
            ["get", "person_index"],
            0, PERSON_COLORS[0],
            1, PERSON_COLORS[1],
            2, PERSON_COLORS[2],
            3, PERSON_COLORS[3],
            "#ffffff",
          ],
        },
      });

      map.addLayer({
        id: "routes-layer",
        type: "line",
        source: "routes-src",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-width": 3.5,
          "line-color": [
            "match",
            ["get", "person_index"],
            0, PERSON_COLORS[0],
            1, PERSON_COLORS[1],
            2, PERSON_COLORS[2],
            3, PERSON_COLORS[3],
            "#ffffff",
          ],
        },
      });
    });

    mapRef.current = map;
  }, []);

  // 2. Gọi API /solve và /wavefront mỗi khi vị trí, alpha hoặc giờ giao thông thay đổi
  const fetchEngineData = useCallback(async () => {
    try {
      const payload = {
        people,
        alpha,
        depart_hour: isRushHour ? 17.5 : null,
        amenity_filter: amenity,
      };

      const [resSolve, resWave] = await Promise.all([
        fetch(`${API_BASE}/api/solve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
        fetch(`${API_BASE}/api/wavefront`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
      ]);

      const dataSolve = await resSolve.json();
      const dataWave = await resWave.json();

      setSolveData(dataSolve);
      setWavefrontData(dataWave.geojson);

      const peakTime = Math.ceil((dataWave.meeting_time_min || 10) + 1);
      setMaxWaveTime(peakTime);
      setCurrentTime(peakTime);

      // Cập nhật tuyến đường và điểm tối ưu lên bản đồ
      const map = mapRef.current;
      if (map && map.getSource("routes-src")) {
        (map.getSource("routes-src") as maplibregl.GeoJSONSource).setData(dataSolve.routes);
      }

      if (map && dataSolve.optimum) {
        if (optMarkerRef.current) optMarkerRef.current.remove();
        const el = document.createElement("div");
        el.className = "w-6 h-6 rounded-full bg-rose-500 border-2 border-white shadow-[0_0_20px_#f43f5e] animate-pulse";
        optMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat([dataSolve.optimum.lng, dataSolve.optimum.lat])
          .addTo(map);
      }
    } catch (err) {
      console.error("Lỗi kết nối Engine API:", err);
    }
  }, [people, alpha, isRushHour, amenity]);

  useEffect(() => {
    fetchEngineData();
  }, [fetchEngineData]);

  // 3. Vẽ các ghim người dùng (cho phép kéo thả trực tiếp)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = people.map((p, idx) => {
      const el = document.createElement("div");
      el.style.backgroundColor = PERSON_COLORS[idx % PERSON_COLORS.length];
      el.className = "w-5 h-5 rounded-full border-2 border-slate-950 shadow-lg cursor-grab flex items-center justify-center text-[10px] font-bold text-slate-950";
      el.innerText = String(idx + 1);

      const marker = new maplibregl.Marker({ element: el, draggable: true })
        .setLngLat([p.lng, p.lat])
        .addTo(map);

      marker.on("dragend", () => {
        const lngLat = marker.getLngLat();
        setPeople((prev) =>
          prev.map((item, i) => (i === idx ? { ...item, lat: lngLat.lat, lng: lngLat.lng } : item))
        );
      });

      return marker;
    });
  }, [people]);

  // 4. Cập nhật lớp phủ Nước Loang theo thanh trượt thời gian currentTime
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !wavefrontData || !map.getSource("wavefront-src")) return;

    const filteredFeatures = wavefrontData.features.filter(
      (f: any) => f.properties.t <= currentTime
    );
    (map.getSource("wavefront-src") as maplibregl.GeoJSONSource).setData({
      type: "FeatureCollection",
      features: filteredFeatures,
    });
  }, [currentTime, wavefrontData]);

  // 5. Vòng lặp Play/Pause Animation
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setCurrentTime((prev) => {
        if (prev >= maxWaveTime) {
          setIsPlaying(false);
          return maxWaveTime;
        }
        return Number((prev + 0.25).toFixed(2));
      });
    }, 50);
    return () => clearInterval(timer);
  }, [isPlaying, maxWaveTime]);

  const handleSelectPoi = (poi: any) => {
    setSelectedPoi(poi);
    const map = mapRef.current;
    if (!map) return;
    if (poiMarkerRef.current) poiMarkerRef.current.remove();

    const el = document.createElement("div");
    el.className = "px-2 py-1 rounded bg-amber-400 text-slate-950 font-bold text-xs shadow-lg border border-white";
    el.innerText = `★ ${poi.name}`;

    poiMarkerRef.current = new maplibregl.Marker({ element: el })
      .setLngLat([poi.lng, poi.lat])
      .addTo(map);

    map.flyTo({ center: [poi.lng, poi.lat], zoom: 14.5, duration: 800 });
  };

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* SIDEBAR ĐIỀU KHIỂN BÊN TRÁI */}
      <div className="w-[400px] h-full bg-slate-900/90 backdrop-blur-md border-r border-slate-800 flex flex-col z-10 overflow-y-auto p-4 gap-4">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            <Navigation className="w-5 h-5 text-cyan-400" />
            Meeting Point Engine
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Đồ thị TP.HCM (14,104 đỉnh) • Tính toán:{" "}
            <span className="text-emerald-400 font-mono">{solveData?.compute_ms ?? "..."} ms</span>
          </p>
        </div>

        {/* Danh sách thành viên */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" /> Thành viên (Kéo ghim trên map)
            </span>
          </div>
          <div className="space-y-1.5">
            {people.map((p, idx) => {
              const tVal = solveData?.times_per_person?.[idx]?.minutes;
              return (
                <div key={idx} className="flex items-center justify-between text-sm bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ backgroundColor: PERSON_COLORS[idx % PERSON_COLORS.length] }}
                    />
                    <span className="font-medium text-slate-200">{p.name}</span>
                  </div>
                  <span className="font-mono text-xs text-cyan-300 font-semibold">
                    {tVal !== undefined ? `${tVal} phút` : "--"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bộ điều khiển Pareto & Giờ giao thông */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400 flex items-center gap-1">
                <Sliders className="w-3.5 h-3.5" /> Mục tiêu Pareto (α = {alpha})
              </span>
              <span className="text-cyan-400 font-medium">
                {alpha === 0 ? "Tổng nhỏ nhất" : alpha === 1 ? "Công bằng nhất" : "Cân bằng"}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={alpha}
              onChange={(e) => setAlpha(parseFloat(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>Ưu tiên Tổng (Sum)</span>
              <span>Ưu tiên Công bằng (Minimax)</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-800">
            <span className="text-xs text-slate-300 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-400" /> Giờ cao điểm (17:30)
            </span>
            <button
              onClick={() => setIsRushHour(!isRushHour)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                isRushHour ? "bg-amber-500 text-slate-950" : "bg-slate-800 text-slate-400"
              }`}
            >
              {isRushHour ? "ĐANG BẬT (×1.85)" : "TẮT (Thấp điểm)"}
            </button>
          </div>
        </div>

        {/* Điều khiển Animation Nước Loang */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">
              Mô phỏng Nước loang: <span className="text-cyan-400 font-mono">{currentTime.toFixed(1)}p</span>
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => {
                  if (currentTime >= maxWaveTime) setCurrentTime(0);
                  setIsPlaying(!isPlaying);
                }}
                className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30"
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => {
                  setIsPlaying(false);
                  setCurrentTime(0);
                }}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <input
            type="range"
            min="0"
            max={maxWaveTime}
            step="0.2"
            value={currentTime}
            onChange={(e) => {
              setIsPlaying(false);
              setCurrentTime(parseFloat(e.target.value));
            }}
            className="w-full accent-rose-500 cursor-pointer"
          />
        </div>

        {/* Top Địa điểm thực tế (POIs) */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Coffee className="w-3.5 h-3.5 text-amber-400" /> Top Địa điểm đề xuất
            </span>
            <select
              value={amenity}
              onChange={(e) => setAmenity(e.target.value)}
              className="bg-slate-800 text-xs text-slate-200 rounded px-2 py-1 border border-slate-700"
            >
              <option value="cafe">Quán Cà phê</option>
              <option value="restaurant">Nhà hàng</option>
              <option value="all">Tất cả</option>
            </select>
          </div>

          <div className="space-y-2 overflow-y-auto pr-1">
            {solveData?.top_pois?.map((poi: any, idx: number) => (
              <div
                key={idx}
                onClick={() => handleSelectPoi(poi)}
                className={`p-2.5 rounded-xl border cursor-pointer transition ${
                  selectedPoi?.name === poi.name
                    ? "bg-cyan-950/40 border-cyan-500"
                    : "bg-slate-900/80 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-semibold text-sm text-white">
                    #{idx + 1} {poi.name}
                  </span>
                  <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-amber-300">
                    Max {poi.f_max}p
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1 flex justify-between">
                  <span>Tổng nhóm: {poi.f_sum}p</span>
                  <span>Score: {poi.score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* BẢN ĐỒ MAPLIBRE DARK MODE BÊN PHẢI */}
      <div className="flex-1 h-full relative">
        <div ref={mapContainer} className="w-full h-full" />

        {/* Thẻ thống kê nổi góc trên bên phải */}
        {solveData?.optimum && (
          <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl px-4 py-3 shadow-2xl">
            <div className="text-[11px] uppercase tracking-wider text-slate-400">Điểm hẹn tối ưu hiện tại</div>
            <div className="flex items-baseline gap-4 mt-1">
              <div>
                <span className="text-xl font-bold text-rose-400">{solveData.optimum.f_max}p</span>
                <span className="text-xs text-slate-400 ml-1">lâu nhất</span>
              </div>
              <div className="h-4 w-[1px] bg-slate-700" />
              <div>
                <span className="text-xl font-bold text-cyan-400">{solveData.optimum.f_sum}p</span>
                <span className="text-xs text-slate-400 ml-1">tổng nhóm</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}