"use client";

import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  Link2,
  Loader2,
  MapPin,
  MessageSquareQuote,
  Play,
  PlayCircle,
  Plus,
  Scale,
  Star,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { attachTikTokLink } from "@/lib/api";
import { ROUTE_PALETTE } from "@/lib/geo";
import { KolVideo, PoiEnrichment, PoiItem } from "@/types/meeting";

interface PoiDetailDrawerProps {
  poi: PoiItem;
  enrichment: PoiEnrichment | null;
  isLoading: boolean;
  onClose: () => void;
}

const HEADER_LABELS: Record<string, string> = {
  cafe: "Quán Cà Phê",
  restaurant: "Nhà Hàng / Quán Ăn",
  sports: "Sân Bóng / Khu Thể Thao",
  entertainment: "Khu Giải Trí / TTTM / Công Viên",
  custom: "Địa Điểm Tự Chọn Trên Bản Đồ",
};

export function PoiDetailDrawer({ poi, enrichment, isLoading, onClose }: PoiDetailDrawerProps) {
  const [localEnrichment, setLocalEnrichment] = useState<PoiEnrichment | null>(enrichment);
  const [playingVideo, setPlayingVideo] = useState<KolVideo | null>(null);
  const [showPasteBox, setShowPasteBox] = useState(false);
  const [tiktokInput, setTiktokInput] = useState("");
  const [attaching, setAttaching] = useState(false);
  const [attachError, setAttachError] = useState("");

  useEffect(() => {
    setLocalEnrichment(enrichment);
  }, [enrichment]);

  useEffect(() => {
    setPlayingVideo(null);
    setShowPasteBox(false);
    setTiktokInput("");
    setAttachError("");
  }, [poi.poi_id, poi.name]);

  const catLabel = HEADER_LABELS[poi.category || poi.amenity] || "Địa Điểm Gặp Mặt";
  const times = poi.person_times?.map((p) => p.minutes) || [];
  const spreadMin = times.length >= 2 ? Number((Math.max(...times) - Math.min(...times)).toFixed(1)) : 0;

  const tiktokSearchUrl =
    localEnrichment?.search_links?.tiktok ||
    `https://www.tiktok.com/search?q=${encodeURIComponent(`${poi.name} ${poi.street} review`)}`;

  const handleAttachTikTok = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tiktokInput.trim()) return;
    setAttaching(true);
    setAttachError("");
    try {
      const updated = await attachTikTokLink(poi.name, poi.street || poi.address, tiktokInput.trim());
      setLocalEnrichment(updated);
      setTiktokInput("");
      setShowPasteBox(false);
    } catch {
      setAttachError("Link TikTok chưa đúng định dạng (ví dụ: https://www.tiktok.com/@user/video/...)");
    } finally {
      setAttaching(false);
    }
  };

  return (
    <div className="absolute top-4 right-4 bottom-4 w-105 bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-md shadow-2xl z-30 flex flex-col overflow-hidden">
      {/* HEADER ĐỊA ĐIỂM */}
      <div className="relative p-5 bg-zinc-950 border-b border-zinc-800">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="text-[11px] font-medium text-sky-400 mb-1">
          {catLabel}
          {poi.cuisine ? ` · ${poi.cuisine}` : ""}
        </div>
        <h2 className="text-lg font-bold text-white pr-8 leading-snug">{poi.name}</h2>
        <p className="text-xs text-zinc-400 mt-1 flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          {poi.address}
        </p>

        {poi.opening_hours && (
          <div className="mt-2.5 text-xs text-zinc-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            <span>Giờ mở cửa: {poi.opening_hours}</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* 1. BẢNG CHỈ SỐ ĐÁNH GIÁ TRỰC QUAN 3 GIÂY */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-zinc-950 border border-zinc-800/90 rounded-md p-2.5">
            <div className="text-[10px] text-zinc-400 flex items-center gap-1">
              <Star className="w-3 h-3 text-amber-400 fill-amber-400" /> Đánh giá
            </div>
            <div className="mt-1 text-sm font-bold text-white tabular-nums">
              {localEnrichment?.rating ? `${localEnrichment.rating} / 5` : "Chưa có điểm"}
            </div>
            <div className="text-[10px] text-zinc-500 truncate mt-0.5">
              {localEnrichment?.review_count
                ? `${localEnrichment.review_count.toLocaleString()} lượt`
                : "Tổng hợp web"}
            </div>
          </div>

          <div className="bg-zinc-950 border border-zinc-800/90 rounded-md p-2.5">
            <div className="text-[10px] text-zinc-400 flex items-center gap-1">
              <Wallet className="w-3 h-3 text-emerald-400" /> Mức giá
            </div>
            <div className="mt-1 text-sm font-bold text-white tabular-nums truncate">
              {localEnrichment?.price_level || "Xem thực đơn"}
            </div>
            <div className="text-[10px] text-zinc-500 truncate mt-0.5">Tham khảo</div>
          </div>

          <div className="bg-zinc-950 border border-zinc-800/90 rounded-md p-2.5">
            <div className="text-[10px] text-zinc-400 flex items-center gap-1">
              <Scale className="w-3 h-3 text-sky-400" /> Độ chênh nhóm
            </div>
            <div className="mt-1 text-sm font-bold text-white tabular-nums">
              {spreadMin} phút
            </div>
            <div className="text-[10px] text-zinc-500 truncate mt-0.5">
              {spreadMin <= 6 ? "Rất cân bằng" : spreadMin <= 12 ? "Chấp nhận được" : "Hơi lệch tuyến"}
            </div>
          </div>
        </div>

        {/* 2. TÓM TẮT NHANH TỪ REVIEW (KHÔNG CẦN XEM HẾT VIDEO) */}
        {((localEnrichment?.highlights && localEnrichment.highlights.length > 0) ||
          (localEnrichment?.review_snippets && localEnrichment.review_snippets.length > 0)) && (
          <div className="bg-zinc-950/90 border border-zinc-800/90 rounded-md p-3.5 space-y-2.5">
            <div className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Điểm nổi bật được nhắc nhiều
            </div>

            {localEnrichment.highlights && localEnrichment.highlights.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {localEnrichment.highlights.map((tag, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-md bg-sky-500/10 border border-sky-500/25 text-[11px] font-medium text-sky-300"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}

            {localEnrichment.review_snippets && localEnrichment.review_snippets.length > 0 && (
              <div className="space-y-1.5 pt-1 border-t border-zinc-800/80">
                {localEnrichment.review_snippets.map((snip, i) => (
                  <p key={i} className="text-[11px] text-zinc-400 leading-relaxed flex items-start gap-1.5">
                    <MessageSquareQuote className="w-3.5 h-3.5 text-zinc-500 shrink-0 mt-0.5" />
                    <span className="line-clamp-2">&quot;{snip}&quot;</span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 3. THỜI GIAN & QUÃNG ĐƯỜNG TỪNG THÀNH VIÊN */}
        <div>
          <h3 className="text-xs font-semibold text-zinc-400 mb-2 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-zinc-400" />
            Thời gian di chuyển từng người
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {poi.person_times?.map((pt, i) => (
              <div
                key={i}
                className="bg-zinc-950 border border-zinc-800/90 rounded-md px-3 py-2 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: ROUTE_PALETTE[i % ROUTE_PALETTE.length] }}
                  />
                  <span className="text-xs font-medium text-zinc-200">{pt.name}</span>
                </div>
                <div className="text-right tabular-nums">
                  <span className="text-xs font-mono font-semibold text-white">{pt.minutes}p</span>
                  {pt.km !== undefined && (
                    <span className="text-[10px] text-zinc-500 ml-1">({pt.km}km)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 4. SHORT VIDEO TIKTOK + DÁN LINK TIKTOK NHANH */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
              <PlayCircle className="w-3.5 h-3.5 text-rose-400" />
              Video Review thực tế
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPasteBox((v) => !v)}
                className="text-[11px] font-medium text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-2 py-1 rounded-md flex items-center gap-1 transition"
              >
                <Plus className="w-3 h-3" /> Gắn link TikTok
              </button>
              <a
                href={tiktokSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-medium text-sky-400 hover:text-sky-300 flex items-center gap-1"
              >
                TikTok <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {showPasteBox && (
            <form onSubmit={handleAttachTikTok} className="mb-3 bg-zinc-950 border border-zinc-700 rounded-md p-2.5 space-y-2">
              <div className="flex items-center gap-1.5">
                <Link2 className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                <input
                  value={tiktokInput}
                  onChange={(e) => setTiktokInput(e.target.value)}
                  placeholder="Dán link video TikTok của quán vào đây..."
                  className="flex-1 bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={attaching}
                  className="px-2.5 py-1 rounded-md bg-sky-500 hover:bg-sky-400 text-zinc-950 text-xs font-semibold disabled:opacity-50"
                >
                  {attaching ? "Đang lưu..." : "Lưu"}
                </button>
              </div>
              {attachError && <p className="text-[11px] text-rose-400">{attachError}</p>}
            </form>
          )}

          {playingVideo && playingVideo.embed_url && (
            <div className="mb-3 bg-zinc-950 border border-zinc-700 rounded-md overflow-hidden">
              <div className="px-3 py-2 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between text-xs">
                <span className="font-medium text-zinc-200 truncate pr-2">
                  {playingVideo.channel_title}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <a
                    href={playingVideo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-sky-400 hover:underline"
                  >
                    Mở TikTok
                  </a>
                  <button
                    onClick={() => setPlayingVideo(null)}
                    className="text-zinc-400 hover:text-white p-0.5"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="w-full h-115 bg-black">
                <iframe
                  src={playingVideo.embed_url}
                  className="w-full h-full border-0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="bg-zinc-950 border border-zinc-800/90 rounded-md p-5 text-xs text-zinc-400 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
              <span>Đang tổng hợp đánh giá & video TikTok cho {poi.name}...</span>
            </div>
          ) : localEnrichment?.kol_videos && localEnrichment.kol_videos.length > 0 ? (
            <div className="grid grid-cols-2 gap-2.5">
              {localEnrichment.kol_videos.map((vid) => {
                const isTikTok = vid.platform !== "youtube";
                return (
                  <div
                    key={vid.video_id}
                    onClick={() => setPlayingVideo(vid)}
                    className="relative aspect-9/16 rounded-md overflow-hidden bg-zinc-950 border border-zinc-800 hover:border-sky-500/70 cursor-pointer group"
                  >
                    {vid.thumbnail ? (
                      <img
                        src={vid.thumbnail}
                        alt={vid.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full bg-zinc-900 flex items-center justify-center text-zinc-600 text-xs">
                        Video Review
                      </div>
                    )}

                    <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/20 to-transparent" />

                    <div className="absolute top-2 left-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold tracking-tight ${
                          isTikTok
                            ? "bg-black/85 text-white border border-white/25"
                            : "bg-rose-600/90 text-white"
                        }`}
                      >
                        {isTikTok ? "TikTok" : "Shorts"}
                      </span>
                    </div>

                    <div className="absolute inset-0 flex items-center justify-center opacity-85 group-hover:opacity-100 transition">
                      <div className="w-9 h-9 rounded-full bg-black/60 backdrop-blur-sm border border-white/30 flex items-center justify-center text-white">
                        <Play className="w-4 h-4 fill-white ml-0.5" />
                      </div>
                    </div>

                    <div className="absolute bottom-2.5 left-2.5 right-2.5">
                      <div className="text-[11px] font-semibold text-white truncate">
                        {vid.channel_title}
                      </div>
                      <p className="text-[10px] text-zinc-300 line-clamp-2 leading-snug mt-0.5">
                        {vid.title}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-zinc-950 border border-zinc-800/90 rounded-md p-3.5 space-y-2.5">
              <p className="text-xs text-zinc-400 leading-relaxed">
                Chưa tìm thấy video tự động cho quán này. Bạn có thể bấm mở nhanh trên TikTok hoặc dán link video vào nút phía trên:
              </p>
              <a
                href={tiktokSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-2 px-3 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs font-semibold text-white flex items-center justify-center gap-1.5 transition"
              >
                Tìm review trên TikTok <ExternalLink className="w-3.5 h-3.5 text-rose-400" />
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}