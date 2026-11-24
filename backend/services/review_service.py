import asyncio
import json
import re
from urllib.parse import quote_plus, unquote
import httpx
from backend.db.sqlite_cache import storage

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

ASPECT_KEYWORDS = [
    ("Không gian rộng", ("rộng rãi", "thoáng", "mát mẻ", "nhiều tầng", "sân vườn", "không gian đẹp")),
    ("Đồ ăn / Nước ngon", ("ngon", "đậm đà", "chất lượng", "tươi", "cuốn", "đặc sản", "nổi tiếng")),
    ("Giá hợp lý", ("giá rẻ", "bình dân", "hợp lý", "phải chăng", "sinh viên", "vừa túi tiền")),
    ("Phục vụ nhanh", ("nhiệt tình", "nhanh nhẹn", "thân thiện", "chu đáo", "lên món nhanh")),
    ("Sống ảo / View đẹp", ("check-in", "sống ảo", "view đẹp", "chill", "ánh sáng", "decor")),
    ("Dễ gửi xe", ("gửi xe", "chỗ đậu xe", "bãi xe", "rộng xe")),
    ("Đông giờ cao điểm", ("đông khách", "xếp hàng", "chờ bàn", "khá đông")),
]


def _simplify_place_name(name: str) -> str:
    """Rút gọn tiền tố hành chính để khớp đúng cách người dùng đặt tiêu đề trên TikTok."""
    prefixes = (
        "nhà hàng ", "quán ăn ", "quán ", "cà phê ", "cafe ", "coffee ",
        "tiệm ", "sân bóng đá ", "sân bóng ", "sân ", "trung tâm thương mại ",
    )
    lower = name.lower().strip()
    for p in prefixes:
        if lower.startswith(p) and len(name) > len(p) + 2:
            return name[len(p):].strip()
    return name.strip()


async def fetch_tiktok_video_by_url(tiktok_url: str) -> dict | None:
    """Lấy metadata thật từ bất kỳ link TikTok nào qua Official oEmbed API."""
    clean_url = tiktok_url.split("?")[0].strip()
    match = re.search(r"tiktok\.com/@([a-zA-Z0-9_.-]+)/video/(\d{15,22})", clean_url)
    author = match.group(1) if match else "tiktok_reviewer"
    video_id = match.group(2) if match else str(abs(hash(clean_url)))

    try:
        async with httpx.AsyncClient(timeout=6.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.get("https://www.tiktok.com/oembed", params={"url": clean_url})
            if resp.status_code != 200:
                return None
            data = resp.json()
            author_name = data.get("author_unique_id") or author
            title = (data.get("title") or "").strip() or f"Review thực tế bởi @{author_name}"
            embed_id_match = re.search(r"/video/(\d{15,22})", data.get("html", ""))
            real_vid = embed_id_match.group(1) if embed_id_match else video_id
            return {
                "platform": "tiktok",
                "video_id": real_vid,
                "title": title,
                "channel_title": f"@{author_name}",
                "published_at": "TikTok",
                "thumbnail": data.get("thumbnail_url") or "",
                "url": clean_url,
                "embed_url": f"https://www.tiktok.com/embed/v3/{real_vid}",
            }
    except Exception:
        return None


async def _fetch_tiktok_oembed(client: httpx.AsyncClient, author: str, video_id: str) -> dict | None:
    clean_url = f"https://www.tiktok.com/@{author}/video/{video_id}"
    try:
        resp = await client.get("https://www.tiktok.com/oembed", params={"url": clean_url}, timeout=5.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        title = (data.get("title") or "").strip() or f"Review tại @{author}"
        return {
            "platform": "tiktok",
            "video_id": video_id,
            "title": title,
            "channel_title": f"@{author}",
            "published_at": "TikTok",
            "thumbnail": data.get("thumbnail_url") or "",
            "url": clean_url,
            "embed_url": f"https://www.tiktok.com/embed/v3/{video_id}",
        }
    except Exception:
        return None


async def _query_search_html(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None,
    data: dict | None = None,
) -> str:
    try:
        if data is not None:
            resp = await client.post(url, data=data, timeout=6.0)
        else:
            resp = await client.get(url, params=params, timeout=6.0)
        return unquote(resp.text) if resp.status_code == 200 else ""
    except Exception:
        return ""


async def _search_tiktok_multi_engine(poi_name: str, street: str, limit: int = 4) -> list[dict]:
    """Quét song song Brave Search, Bing và DuckDuckGo Lite để tìm link video TikTok thật."""
    short_name = _simplify_place_name(poi_name)
    main_street = street.split(",")[0].strip()

    q1 = f'site:tiktok.com "{short_name}" {main_street}'
    q2 = f'site:tiktok.com "{short_name}" review sài gòn'

    async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True) as client:
        html_pages = await asyncio.gather(
            _query_search_html(client, "https://search.brave.com/search", params={"q": q1, "source": "web"}),
            _query_search_html(client, "https://www.bing.com/search", params={"q": q1}),
            _query_search_html(client, "https://www.bing.com/search", params={"q": q2}),
            _query_search_html(client, "https://lite.duckduckgo.com/lite/", data={"q": q2}),
        )

        found_pairs: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        for html in html_pages:
            if not html:
                continue
            for author, vid in re.findall(
                r"tiktok\.com/@([a-zA-Z0-9_.-]+)/video/(\d{15,22})", html
            ):
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    found_pairs.append((author, vid))
                if len(found_pairs) >= limit + 2:
                    break

        if not found_pairs:
            return []

        oembed_tasks = [_fetch_tiktok_oembed(client, a, v) for a, v in found_pairs[: limit + 2]]
        verified = await asyncio.gather(*oembed_tasks)
        return [item for item in verified if item is not None][:limit]


async def _search_web_rating_and_snippets(poi_name: str, street: str) -> dict:
    """Trích xuất điểm đánh giá thật (x/5), khoảng giá và nhận xét ngắn từ kết quả web."""
    short_name = _simplify_place_name(poi_name)
    main_street = street.split(",")[0].strip()
    query = f'"{short_name}" {main_street} đánh giá review'

    async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True) as client:
        html_list = await asyncio.gather(
            _query_search_html(client, "https://www.bing.com/search", params={"q": query}),
            _query_search_html(client, "https://search.brave.com/search", params={"q": query}),
        )

    combined = "\n".join(html_list)
    text_only = re.sub(r"<[^>]+>", " ", combined)
    text_only = re.sub(r"\s+", " ", text_only)

    # 1. Tìm điểm rating thật (ví dụ: 4.5/5, 4,4 / 5, Rating: 4.6)
    rating = None
    for pat in (
        r"(?:Rating|Đánh giá|Điểm)[:\s]*([34]\.\d)\s*/\s*5",
        r"\b([34]\.\d)\s*/\s*5\b",
        r"\b([34],\d)\s*/\s*5\b",
    ):
        m = re.search(pat, text_only, re.IGNORECASE)
        if m:
            rating = float(m.group(1).replace(",", "."))
            break

    # 2. Tìm số lượt đánh giá nếu có
    review_count = None
    m_cnt = re.search(r"\((\d{1,3}(?:[.,]\d{3})*)\s*(?:đánh giá|nhận xét|reviews?)\)", text_only, re.IGNORECASE)
    if m_cnt:
        review_count = int(m_cnt.group(1).replace(".", "").replace(",", ""))

    # 3. Tìm khoảng giá tham khảo (ví dụ: 50.000đ - 150.000đ hoặc 40k - 80k)
    price_level = None
    m_price = re.search(
        r"(\d{2,3}(?:\.000|k))\s*[-–~]\s*(\d{2,3}(?:\.000|k))",
        text_only,
        re.IGNORECASE,
    )
    if m_price:
        p1 = m_price.group(1).replace(".000", "k")
        p2 = m_price.group(2).replace(".000", "k")
        price_level = f"{p1} – {p2}"

    # 4. Trích xuất 2-3 đoạn nhận xét ngắn chứa tên quán
    snippets = []
    sentences = re.split(r"(?<=[.!?])\s+", text_only)
    short_lower = short_name.lower()
    for s in sentences:
        s_clean = s.strip()
        if (
            45 <= len(s_clean) <= 170
            and short_lower in s_clean.lower()
            and not any(bad in s_clean.lower() for bad in ("http", "bing", "brave", "cookie", "privacy", "đăng nhập"))
        ):
            if s_clean not in snippets:
                snippets.append(s_clean)
        if len(snippets) >= 2:
            break

    return {
        "rating": rating,
        "review_count": review_count,
        "price_level": price_level,
        "snippets": snippets,
        "raw_corpus": text_only,
    }


def _extract_highlight_tags(corpus: str) -> list[str]:
    lower = corpus.lower()
    tags = []
    for label, keywords in ASPECT_KEYWORDS:
        if any(kw in lower for kw in keywords):
            tags.append(label)
    return tags[:5]


async def _search_youtube_shorts_fallback(query: str, limit: int = 2) -> list[dict]:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        async with httpx.AsyncClient(timeout=6.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []

        match = re.search(r"var ytInitialData\s*=\s*(\{.*?\});</script>", resp.text)
        if not match:
            return []

        data = json.loads(match.group(1))
        sections = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        videos = []
        for sec in sections:
            items = sec.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                vr = item.get("videoRenderer")
                if not vr:
                    continue
                vid = vr.get("videoId")
                title_runs = vr.get("title", {}).get("runs", [])
                title = "".join(r.get("text", "") for r in title_runs).strip()
                owner_runs = vr.get("ownerText", {}).get("runs", [])
                channel = owner_runs[0].get("text", "Shorts") if owner_runs else "Shorts"
                thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
                thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                if vid and title:
                    videos.append({
                        "platform": "youtube",
                        "video_id": vid,
                        "title": title,
                        "channel_title": channel,
                        "published_at": "Shorts",
                        "thumbnail": thumb_url,
                        "url": f"https://www.youtube.com/shorts/{vid}",
                        "embed_url": f"https://www.youtube.com/embed/{vid}",
                    })
                if len(videos) >= limit:
                    return videos
        return videos
    except Exception:
        return []


async def fetch_real_poi_enrichment(poi_name: str, street: str, lat: float, lng: float) -> dict:
    poi_key = f"v4_ux|{poi_name.lower().strip()}|{street.lower().strip()}"
    cached = storage.get_poi_enrichment(poi_key)
    if cached is not None:
        return cached

    short_name = _simplify_place_name(poi_name)
    main_street = street.split(",")[0].strip()

    tiktok_videos, insights = await asyncio.gather(
        _search_tiktok_multi_engine(poi_name, street, limit=4),
        _search_web_rating_and_snippets(poi_name, street),
    )

    videos = list(tiktok_videos)
    if len(videos) < 2:
        shorts = await _search_youtube_shorts_fallback(
            f"{short_name} {main_street} review #shorts",
            limit=2 - len(videos),
        )
        videos.extend(shorts)

    full_text = insights.get("raw_corpus", "") + " " + " ".join(v.get("title", "") for v in videos)
    highlights = _extract_highlight_tags(full_text)

    tiktok_q = quote_plus(f"{short_name} {main_street} review")
    youtube_q = quote_plus(f"{short_name} review #shorts")
    gmaps_q = quote_plus(f"{poi_name} {street}")

    enrichment = {
        "rating": insights.get("rating"),
        "review_count": insights.get("review_count"),
        "price_level": insights.get("price_level"),
        "photo_url": None,
        "highlights": highlights,
        "review_snippets": insights.get("snippets", []),
        "kol_videos": videos,
        "search_links": {
            "tiktok": f"https://www.tiktok.com/search?q={tiktok_q}",
            "youtube": f"https://www.youtube.com/results?search_query={youtube_q}",
            "google_maps": f"https://www.google.com/maps/search/?api=1&query={gmaps_q}",
        },
    }

    storage.save_poi_enrichment(poi_key, enrichment)
    return enrichment


async def attach_manual_tiktok_to_poi(poi_name: str, street: str, tiktok_url: str) -> dict | None:
    """Cho phép người dùng dán trực tiếp link TikTok vào địa điểm và lưu cache."""
    video = await fetch_tiktok_video_by_url(tiktok_url)
    if not video:
        return None

    short_name = _simplify_place_name(poi_name)
    main_street = street.split(",")[0].strip()
    poi_key = f"v4_ux|{poi_name.lower().strip()}|{street.lower().strip()}"

    existing = storage.get_poi_enrichment(poi_key) or {
        "rating": None,
        "review_count": None,
        "price_level": None,
        "photo_url": None,
        "highlights": [],
        "review_snippets": [],
        "kol_videos": [],
        "search_links": {
            "tiktok": f"https://www.tiktok.com/search?q={quote_plus(f'{short_name} {main_street} review')}",
            "youtube": f"https://www.youtube.com/results?search_query={quote_plus(f'{short_name} review #shorts')}",
            "google_maps": f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{poi_name} {street}')}",
        },
    }

    current_videos = [v for v in existing.get("kol_videos", []) if v.get("video_id") != video["video_id"]]
    existing["kol_videos"] = [video] + current_videos[:3]

    new_tags = _extract_highlight_tags(video.get("title", ""))
    merged_tags = list(dict.fromkeys([*existing.get("highlights", []), *new_tags]))[:5]
    existing["highlights"] = merged_tags

    storage.save_poi_enrichment(poi_key, existing)
    return existing