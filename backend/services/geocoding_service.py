import math
import unicodedata
import httpx
import numpy as np
import asyncio
from backend.services.graph_engine import GraphEngine
import sqlite3
import os
import json

HEADERS = {
    "User-Agent": "MeetPointHCMC/4.0 (urban-routing-research)",
    "Accept": "application/json",
}

HCMC_LANDMARKS = [
    {"label": "Đại học Công nghiệp TP.HCM (IUH), 12 Nguyễn Văn Bảo, Gò Vấp", "lat": 10.8222, "lng": 106.6875},
    {"label": "Chợ Bến Thành, Quận 1", "lat": 10.7725, "lng": 106.6980},
    {"label": "Hồ Con Rùa, Công trường Quốc Tế, Quận 3", "lat": 10.7827, "lng": 106.6959},
    {"label": "Nhà thờ Đức Bà Sài Gòn, Quận 1", "lat": 10.7798, "lng": 106.6990},
    {"label": "Phố đi bộ Nguyễn Huệ, Quận 1", "lat": 10.7744, "lng": 106.7035},
    {"label": "Landmark 81, Vinhomes Central Park, Bình Thạnh", "lat": 10.7950, "lng": 106.7218},
    {"label": "Ngã tư Hàng Xanh, Bình Thạnh", "lat": 10.8013, "lng": 106.7114},
    {"label": "Đường Vạn Kiếp, Bình Thạnh", "lat": 10.7995, "lng": 106.6922},
    {"label": "Đường Phan Xích Long, Phú Nhuận", "lat": 10.7992, "lng": 106.6865},
    {"label": "Vạn Hạnh Mall, 11 Sư Vạn Hạnh, Quận 10", "lat": 10.7709, "lng": 106.6699},
    {"label": "Sân bay Tân Sơn Nhất, Tân Bình", "lat": 10.8185, "lng": 106.6588},
    {"label": "Crescent Mall, Phú Mỹ Hưng, Quận 7", "lat": 10.7289, "lng": 106.7186},
    {"label": "SC VivoCity, 1058 Nguyễn Văn Linh, Quận 7", "lat": 10.7302, "lng": 106.7036},
    {"label": "Lê Văn Lương, Phước Kiển, Nhà Bè", "lat": 10.7035, "lng": 106.7032},
    {"label": "Huỳnh Tấn Phát, Thị trấn Nhà Bè, Nhà Bè", "lat": 10.6845, "lng": 106.7412},
    {"label": "Khu dân cư Trung Sơn, Bình Chánh", "lat": 10.7336, "lng": 106.6889},
    {"label": "Aeon Mall Bình Tân, Đường số 17A, Bình Tân", "lat": 10.7426, "lng": 106.6122},
    {"label": "Vincom Mega Mall Thảo Điền, Thủ Đức", "lat": 10.8022, "lng": 106.7410},
    {"label": "Làng Đại học Quốc gia TP.HCM, Thủ Đức", "lat": 10.8700, "lng": 106.8030},
    {"label": "Đại học Bách Khoa TP.HCM, 268 Lý Thường Kiệt, Quận 10", "lat": 10.7721, "lng": 106.6579},
    {"label": "Đại học Khoa học Tự nhiên, 227 Nguyễn Văn Cừ, Quận 5", "lat": 10.7629, "lng": 106.6822},
]

CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sports": (
        "san bong da", "san bong", "san da banh", "da banh", "bong da", "san banh",
        "san co nhan tao", "cau long", "pickleball", "tennis", "bong ro", "the thao", "gym", "ho boi",
    ),
    "cafe": (
        "ca phe", "cafe", "coffee", "tra sua", "tiem banh", "matcha", "nuoc ep",
    ),
    "restaurant": (
        "quan an", "nha hang", "an uong", "an trua", "an toi", "com", "pho",
        "bun", "lau", "nuong", "oc", "hai san", "banh mi", "hu tieu",
    ),
    "entertainment": (
        "giai tri", "rap phim", "xem phim", "cgv", "lotte", "cong vien",
        "trung tam thuong mai", "tttm", "mall", "karaoke", "bowling",
    ),
}


def _normalize_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _detect_category_intent(q_norm: str) -> str | None:
    for cat, keywords in CATEGORY_SYNONYMS.items():
        if any(kw in q_norm for kw in keywords):
            return cat
    return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _search_arcgis_vn(q_clean: str, focus_lat: float, focus_lng: float, limit: int = 5) -> list[dict]:
    """Geocoder chuyên trị số nhà & tên đường Việt Nam (không cần API key)."""
    try:
        async with httpx.AsyncClient(timeout=4.5, headers=HEADERS) as client:
            resp = await client.get(
                "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
                params={
                    "SingleLine": f"{q_clean}, Hồ Chí Minh, Việt Nam",
                    "f": "json",
                    "countryCode": "VNM",
                    "location": f"{focus_lng},{focus_lat}",
                    "searchExtent": "106.58,10.64,106.82,10.89",
                    "maxLocations": limit,
                    "outFields": "PlaceName,Place_addr,Type",
                },
            )
            if resp.status_code != 200:
                return []
            candidates = resp.json().get("candidates", [])
            out = []
            for c in candidates:
                loc = c.get("location", {})
                lat, lng = loc.get("y"), loc.get("x")
                if lat is None or lng is None:
                    continue
                if not (10.63 <= lat <= 10.90 and 106.57 <= lng <= 106.83):
                    continue
                addr = c.get("address", "")
                addr = addr.replace(", Thành phố Hồ Chí Minh", "").replace(", Hồ Chí Minh", "").replace(", Việt Nam", "")
                if addr:
                    out.append({"label": addr, "lat": float(lat), "lng": float(lng)})
            return out
    except Exception:
        return []

def _get_goong_cache(cache_key: str) -> list[dict] | None:
    db_path = os.getenv("SQLITE_DB_PATH", "data/meetpoint.db")
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS geocode_cache (cache_key TEXT PRIMARY KEY, payload TEXT)"
            )
            row = conn.execute(
                "SELECT payload FROM geocode_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            return json.loads(row[0]) if row else None
    except Exception:
        return None


def _set_goong_cache(cache_key: str, results: list[dict]) -> None:
    if not results:
        return
    db_path = os.getenv("SQLITE_DB_PATH", "data/meetpoint.db")
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS geocode_cache (cache_key TEXT PRIMARY KEY, payload TEXT)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO geocode_cache (cache_key, payload) VALUES (?, ?)",
                (cache_key, json.dumps(results, ensure_ascii=False)),
            )
    except Exception:
        pass


async def _fetch_goong_detail_v2(
    client: httpx.AsyncClient, api_key: str, item: dict
) -> dict | None:
    place_id = item.get("place_id")
    if not place_id:
        return None
    try:
        resp = await client.get(
            "https://rsapi.goong.io/v2/place/detail",
            params={"api_key": api_key, "place_id": place_id},
            timeout=3.5,
        )
        if resp.status_code != 200:
            return None
        result = resp.json().get("result", {})
        loc = result.get("geometry", {}).get("location")
        if not loc:
            return None
        return {
            "label": item.get("description") or result.get("formatted_address", ""),
            "lat": float(loc["lat"]),
            "lng": float(loc["lng"]),
            "source": "goong",
        }
    except Exception:
        return None


async def query_goong_places(
    query: str,
    center_lat: float = 10.7769,
    center_lng: float = 106.7009,
    limit: int = 6,
    radius_km: int = 20,
) -> list[dict]:
    api_key = os.getenv("GOONG_API_KEY", "").strip()
    clean_q = query.strip()
    if not api_key or len(clean_q) < 3:
        return []

    cache_key = f"goong_v2:{clean_q.lower()}:{round(center_lat, 3)}:{round(center_lng, 3)}:r{radius_km}"
    cached = _get_goong_cache(cache_key)
    if cached is not None:
        return cached[:limit]

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://rsapi.goong.io/v2/place/autocomplete",
                params={
                    "api_key": api_key,
                    "input": clean_q,
                    "location": f"{center_lat},{center_lng}",
                    "radius": radius_km,
                    "limit": limit,
                    "has_deprecated_administrative_unit": "true",
                },
                timeout=3.5,
            )
            if resp.status_code != 200:
                return []
            predictions = resp.json().get("predictions", [])[:limit]
            if not predictions:
                return []

            details = await asyncio.gather(
                *[_fetch_goong_detail_v2(client, api_key, item) for item in predictions]
            )
            results = [d for d in details if d is not None]
            _set_goong_cache(cache_key, results)
            return results
    except Exception:
        return []
    
async def forward_geocode(
    q: str,
    engine: GraphEngine,
    focus_lat: float = 10.7769,
    focus_lng: float = 106.7009,
) -> list[dict]:
    results = []
    seen_labels = set()
    q_clean = q.strip()
    q_norm = _normalize_vn(q_clean)
    cat_intent = _detect_category_intent(q_norm)

    def _add_result(
        label: str,
        lat: float,
        lng: float,
        poi_id: int | None = None,
        category: str | None = None,
        source: str | None = None,
    ):
        key = _normalize_vn(label)
        if key in seen_labels:
            return
        seen_labels.add(key)
        item: dict = {"label": label, "lat": float(lat), "lng": float(lng)}
        if poi_id is not None:
            item["poi_id"] = int(poi_id)
        if category:
            item["category"] = category
        if source:
            item["source"] = source
        results.append(item)

    # 1. Địa danh lớn & trường đại học
    for lm in HCMC_LANDMARKS:
        if q_norm in _normalize_vn(lm["label"]):
            _add_result(lm["label"], lm["lat"], lm["lng"])

    # 1.5. Goong Places API v2 (ưu tiên địa chỉ chi tiết & quán mới tại Việt Nam)
    goong_hits = await query_goong_places(q_clean, focus_lat, focus_lng, limit=6)
    for item in goong_hits:
        _add_result(item["label"], item["lat"], item["lng"], source="goong")

    # 2. Tìm trong dữ liệu POI nội bộ (khớp theo cả tên lẫn ý định danh mục & ưu tiên gần tâm bản đồ)
    if not hasattr(engine, "_poi_norm_series"):
        engine._poi_norm_series = (
            engine.df_pois["name"].astype(str) + " " + engine.df_pois["address"].astype(str)
        ).apply(_normalize_vn)

    name_mask = engine._poi_norm_series.str.contains(q_norm, regex=False, na=False)
    if cat_intent:
        cat_col = engine.df_pois["category"] if "category" in engine.df_pois.columns else engine.df_pois["amenity"]
        matched_df = engine.df_pois[name_mask | (cat_col == cat_intent)].copy()
    else:
        matched_df = engine.df_pois[name_mask].copy()

    if not matched_df.empty:
        matched_df["_dist"] = np.hypot(
            (matched_df["lat"] - focus_lat) * 111.0,
            (matched_df["lng"] - focus_lng) * 109.0,
        )
        matched_df = matched_df.sort_values("_dist")
        for _, row in matched_df.head(6).iterrows():
            addr = row["address"] if row["address"] else row["street"]
            cat_val = row.get("category") or row.get("amenity")
            _add_result(f"{row['name']} · {addr}", row["lat"], row["lng"], int(row["poi_id"]), str(cat_val))

    # 3. ArcGIS World Geocoder (tìm cực chuẩn số nhà, hẻm, tên đường VN)
    if len(results) < 6:
        arcgis_hits = await _search_arcgis_vn(q_clean, focus_lat, focus_lng, limit=6)
        for item in arcgis_hits:
            _add_result(item["label"], item["lat"], item["lng"])

    # 4. Photon Komoot (ưu tiên quanh vị trí đang xem trên bản đồ)
    if len(results) < 6:
        try:
            async with httpx.AsyncClient(timeout=4.0, headers=HEADERS) as client:
                resp = await client.get(
                    "https://photon.komoot.io/api/",
                    params={"q": f"{q_clean}, Ho Chi Minh", "lat": focus_lat, "lon": focus_lng, "limit": 5},
                )
                if resp.status_code == 200 and resp.text.strip():
                    for feat in resp.json().get("features", []):
                        props = feat.get("properties", {})
                        coords = feat.get("geometry", {}).get("coordinates", [])
                        if len(coords) < 2:
                            continue
                        house = props.get("housenumber", "")
                        street = props.get("street", "")
                        name = props.get("name") or f"{house} {street}".strip() or q_clean
                        district = props.get("district") or props.get("city", "TP.HCM")
                        street_full = f"{house} {street}".strip()
                        label = ", ".join(
                            filter(None, [name, street_full if street_full != name else "", district])
                        )
                        _add_result(label, coords[1], coords[0])
        except Exception:
            pass

    return results[:9]

async def _query_arcgis_candidates(
    client: httpx.AsyncClient,
    single_line: str,
    center_lat: float,
    center_lng: float,
    extent: str,
    limit: int = 20,
) -> list[dict]:
    try:
        resp = await client.get(
            "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
            params={
                "SingleLine": single_line,
                "f": "json",
                "countryCode": "VNM",
                "location": f"{center_lng},{center_lat}",
                "searchExtent": extent,
                "maxLocations": limit,
                "outFields": "PlaceName,Place_addr,Type",
            },
            timeout=4.5,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("candidates", [])
    except Exception:
        return []


async def _query_photon_candidates(
    client: httpx.AsyncClient,
    query: str,
    center_lat: float,
    center_lng: float,
    limit: int = 15,
) -> list[dict]:
    try:
        resp = await client.get(
            "https://photon.komoot.io/api/",
            params={"q": query, "lat": center_lat, "lon": center_lng, "limit": limit},
            timeout=4.0,
        )
        if resp.status_code != 200 or not resp.text.strip():
            return []
        return resp.json().get("features", [])
    except Exception:
        return []

async def search_places_in_area(
    engine: GraphEngine,
    query: str,
    west: float,
    south: float,
    east: float,
    north: float,
    limit: int = 15,
) -> list[dict]:
    """Tìm địa điểm trong khung nhìn bản đồ với biên đệm 15%, lọc chính xác theo môn thể thao."""
    q_clean = query.strip()
    q_norm = _normalize_vn(q_clean)
    cat_intent = _detect_category_intent(q_norm)

    d_lat = abs(north - south)
    d_lng = abs(east - west)
    pad_lat = max(d_lat * 0.15, 0.002)
    pad_lng = max(d_lng * 0.15, 0.002)
    min_lat = min(south, north) - pad_lat
    max_lat = max(south, north) + pad_lat
    min_lng = min(west, east) - pad_lng
    max_lng = max(west, east) + pad_lng
    center_lat = (south + north) / 2.0
    center_lng = (west + east) / 2.0

    OSM_GARBAGE_NAMES = (
        "cong vao", "bai giu xe", "nha ve sinh", "gui xe", "toilet",
        "parking", "gate", "entrance", "wc", "loi vao",
        "chi cuc", "uy ban", "bao ve moi truong", "so tai nguyen", "tru so",
    )
    FOOTBALL_QUERY_WORDS = (
        "san bong da", "san bong", "san banh", "da banh", "bong da",
        "futsal", "soccer", "football",
    )
    FOOTBALL_MATCH_WORDS = (
        "bong da", "san banh", "futsal", "soccer", "football",
        "co nhan tao", "san 5", "san 7", "san mini",
    )
    OTHER_SPORT_EXCLUSIONS = (
        "badminton", "cau long", "pickleball", "tennis", "bong ro",
        "bong chuyen", "gym", "fitness", "yoga", "boi", "swimming",
        "bida", "billiards", "golf", "climbing",
    )
    BADMINTON_WORDS = ("cau long", "badminton")
    PICKLEBALL_WORDS = ("pickleball",)
    TENNIS_WORDS = ("tennis", "quan vot")
    SWIMMING_WORDS = ("boi", "swimming", "ho boi")
    GYM_WORDS = ("gym", "the hinh", "fitness", "yoga")

    sport_intent = None
    if any(kw in q_norm for kw in FOOTBALL_QUERY_WORDS):
        sport_intent = "football"
    elif any(kw in q_norm for kw in BADMINTON_WORDS):
        sport_intent = "badminton"
    elif any(kw in q_norm for kw in PICKLEBALL_WORDS):
        sport_intent = "pickleball"
    elif any(kw in q_norm for kw in TENNIS_WORDS):
        sport_intent = "tennis"
    elif any(kw in q_norm for kw in SWIMMING_WORDS):
        sport_intent = "swimming"
    elif any(kw in q_norm for kw in GYM_WORDS):
        sport_intent = "gym"

    def _is_match(name_clean: str, sub_type_str: str) -> bool:
        n_norm = _normalize_vn(name_clean)
        s_norm = _normalize_vn(sub_type_str)

        if any(g in n_norm for g in OSM_GARBAGE_NAMES):
            return False

        if sport_intent == "football":
            if any(w in n_norm or w in s_norm for w in FOOTBALL_MATCH_WORDS):
                return True
            if s_norm in ("pitch", "stadium", "soccer", "football") and not any(other in n_norm for other in OTHER_SPORT_EXCLUSIONS):
                return True
            return False

        if sport_intent == "badminton":
            return any(w in n_norm or w in s_norm for w in BADMINTON_WORDS)

        if sport_intent == "pickleball":
            return any(w in n_norm or w in s_norm for w in PICKLEBALL_WORDS)

        if sport_intent == "tennis":
            return any(w in n_norm or w in s_norm for w in TENNIS_WORDS)

        if sport_intent == "swimming":
            return any(w in n_norm or w in s_norm for w in SWIMMING_WORDS)

        if sport_intent == "gym":
            return any(w in n_norm or w in s_norm for w in GYM_WORDS)

        if cat_intent:
            syns = CATEGORY_SYNONYMS.get(cat_intent, ())
            return (cat_intent in s_norm) or any(s in n_norm for s in syns) or (q_norm in n_norm)

        return q_norm in n_norm

    results: list[dict] = []
    seen_keys: set[str] = set()

    def _push_place(
        poi_id: int,
        name: str,
        address: str,
        street: str,
        lat: float,
        lng: float,
        sub_type: str = "",
        opening_hours: str | None = None,
        cuisine: str | None = None,
    ):
        f_lat, f_lng = float(lat), float(lng)
        if not (min_lat <= f_lat <= max_lat and min_lng <= f_lng <= max_lng):
            return
        name_clean = name.strip()
        if not name_clean:
            return
        if not _is_match(name_clean, sub_type):
            return

        key = f"{_normalize_vn(name_clean)}|{round(f_lat, 3)}|{round(f_lng, 3)}"
        if key in seen_keys:
            return
        seen_keys.add(key)

        dist_km = _haversine_km(center_lat, center_lng, f_lat, f_lng)
        matched_cat = sport_intent or cat_intent or "custom"
        results.append({
            "poi_id": poi_id,
            "name": name_clean,
            "amenity": matched_cat,
            "category": matched_cat,
            "sub_type": sub_type or matched_cat,
            "street": street,
            "address": address or street,
            "opening_hours": opening_hours,
            "cuisine": cuisine,
            "lat": f_lat,
            "lng": f_lng,
            "f_sum": 0.0,
            "f_max": 0.0,
            "person_times": [],
            "distance_km": round(dist_km, 2),
        })

    # 1. Tìm trong kho POI nội bộ giới hạn theo khung nhìn [west, south, east, north] (+15% padding)
    df = engine.df_pois
    box_mask = (
        (df["lat"] >= min_lat) & (df["lat"] <= max_lat) &
        (df["lng"] >= min_lng) & (df["lng"] <= max_lng)
    )
    sub = df[box_mask].copy()

    if not sub.empty:
        sub["_dist_km"] = np.hypot(
            (sub["lat"] - center_lat) * 111.0,
            (sub["lng"] - center_lng) * 109.0,
        )
        sub = sub.sort_values("_dist_km")
        for _, row in sub.iterrows():
            oh = str(row.get("opening_hours", ""))
            cu = str(row.get("cuisine", ""))
            _push_place(
                poi_id=int(row["poi_id"]),
                name=str(row["name"]),
                address=str(row.get("address") or row.get("street") or ""),
                street=str(row.get("street") or ""),
                lat=float(row["lat"]),
                lng=float(row["lng"]),
                sub_type=str(row.get("sub_type") or row.get("amenity") or ""),
                opening_hours=None if oh in ("", "nan", "None") else oh,
                cuisine=None if cu in ("", "nan", "None") else cu,
            )

   # 2. Quét trực tiếp từ Goong Places v2 trong bán kính 2km quanh tâm khung nhìn
    idx_counter = 100
    try:
        area_ctx = await reverse_geocode(center_lat, center_lng, engine)
        district = area_ctx.split(",")[-1].strip() if "," in area_ctx else ""

        if sport_intent == "football":
            queries = ["sân bóng đá", "sân bóng", "sân cỏ nhân tạo"]
            if district:
                queries.append(f"sân bóng {district}")
        elif q_norm and q_norm != "all":
            queries = [q_clean]
            if district:
                queries.append(f"{q_clean} {district}")
        else:
            queries = []

        batches = await asyncio.gather(
            *[
                query_goong_places(q_item, center_lat, center_lng, limit=10, radius_km=2)
                for q_item in queries
            ]
        )

        for batch in batches:
            for g in batch:
                g_lat, g_lng = float(g["lat"]), float(g["lng"])
                if min_lat <= g_lat <= max_lat and min_lng <= g_lng <= max_lng:
                    parts = [p.strip() for p in g.get("label", "").split(",")]
                    p_name = parts[0] if parts else g.get("label", "")
                    p_addr = ", ".join(parts[1:]) if len(parts) > 1 else g.get("label", "")
                    _push_place(
                        poi_id=-idx_counter,
                        name=p_name,
                        address=p_addr,
                        street=p_addr or engine.get_nearest_street_label(g_lat, g_lng),
                        lat=g_lat,
                        lng=g_lng,
                        sub_type=sport_intent or cat_intent or "custom",
                    )
                    idx_counter += 1
    except Exception:
        pass

    # 3. Bổ sung thêm từ ArcGIS & Photon nếu chưa đủ kết quả trong khung nhìn
    if len(results) < limit and q_norm and q_norm != "all":
        area_ctx = await reverse_geocode(center_lat, center_lng, engine)
        district = area_ctx.split(",")[-1].strip() if "," in area_ctx else "Hồ Chí Minh"
        extent_str = f"{min_lng},{min_lat},{max_lng},{max_lat}"

        alt_query = "sân bóng" if sport_intent == "football" else q_clean
        async with httpx.AsyncClient(headers=HEADERS) as client:
            c1, c2, photon_feats = await asyncio.gather(
                _query_arcgis_candidates(client, f"{q_clean}, {district}, Hồ Chí Minh", center_lat, center_lng, extent_str),
                _query_arcgis_candidates(client, f"{alt_query}, Hồ Chí Minh", center_lat, center_lng, extent_str),
                _query_photon_candidates(client, f"{alt_query} {district}", center_lat, center_lng),
            )

        for cand in [*c1, *c2]:
            loc = cand.get("location", {})
            lat, lng = loc.get("y"), loc.get("x")
            if lat is None or lng is None:
                continue
            f_lat, f_lng = float(lat), float(lng)
            if not (min_lat <= f_lat <= max_lat and min_lng <= f_lng <= max_lng):
                continue
            attrs = cand.get("attributes", {})
            full_addr = (
                cand.get("address", "")
                .replace(", Thành phố Hồ Chí Minh", "")
                .replace(", Hồ Chí Minh", "")
                .replace(", Việt Nam", "")
            )
            place_name = (attrs.get("PlaceName") or full_addr.split(",")[0]).strip()
            street_label = engine.get_nearest_street_label(f_lat, f_lng)
            _push_place(
                poi_id=-idx_counter,
                name=place_name,
                address=full_addr or street_label,
                street=street_label,
                lat=f_lat,
                lng=f_lng,
                sub_type=attrs.get("Type") or sport_intent or cat_intent or "custom",
            )
            idx_counter += 1

        for feat in photon_feats:
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            f_lat, f_lng = float(coords[1]), float(coords[0])
            if not (min_lat <= f_lat <= max_lat and min_lng <= f_lng <= max_lng):
                continue
            p_name = props.get("name")
            if not p_name:
                continue
            p_street = props.get("street") or engine.get_nearest_street_label(f_lat, f_lng)
            p_dist = props.get("district") or district
            _push_place(
                poi_id=-idx_counter,
                name=str(p_name),
                address=f"{p_street}, {p_dist}",
                street=str(p_street),
                lat=f_lat,
                lng=f_lng,
                sub_type=sport_intent or cat_intent or "custom",
            )
            idx_counter += 1

    # Ưu tiên kết quả có tên khớp rõ ràng sân bóng / môn thể thao lên đầu, sau đó theo khoảng cách
    def _sort_key(place: dict):
        p_name_norm = _normalize_vn(place.get("name", ""))
        p_sub_norm = _normalize_vn(place.get("sub_type", ""))
        if sport_intent == "football":
            # Tier 0: Tên chứa từ khóa sân bóng đá trực tiếp (\bsan bong da\b, \bsan bong\b, \bsan banh\b, futsal, soccer...)
            primary_football_words = ("san bong da", "san bong", "san banh", "da banh", "bong da", "futsal", "soccer", "football", "co nhan tao")
            if any(w in p_name_norm for w in primary_football_words):
                prio = 0
            elif any(w in p_sub_norm for w in primary_football_words) or p_sub_norm in ("pitch", "stadium"):
                prio = 1
            else:
                prio = 2
        elif sport_intent:
            prio = 0 if q_norm in p_name_norm else 1
        else:
            prio = 0 if q_norm in p_name_norm else 1
        return (prio, place.get("distance_km", 99.0))

    results.sort(key=_sort_key)
    return results[:limit]

async def reverse_geocode(lat: float, lng: float, engine: GraphEngine) -> str:
    local_street = engine.get_nearest_street_label(lat, lng)
    try:
        async with httpx.AsyncClient(timeout=3.5, headers=HEADERS) as client:
            resp = await client.get(
                "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/reverseGeocode",
                params={"location": f"{lng},{lat}", "f": "json"},
            )
            if resp.status_code == 200:
                addr = resp.json().get("address", {})
                short_addr = addr.get("ShortLabel") or addr.get("Address")
                district = addr.get("District") or addr.get("Subregion") or "TP.HCM"
                if short_addr:
                    return f"{short_addr}, {district}"
    except Exception:
        pass
    return f"{local_street}, TP.HCM"