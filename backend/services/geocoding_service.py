import math
import unicodedata
import httpx
import numpy as np
import asyncio
from backend.services.graph_engine import GraphEngine

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
        "san bong", "san da banh", "da banh", "bong da", "san co nhan tao",
        "cau long", "pickleball", "tennis", "bong ro", "the thao", "gym", "ho boi",
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

    def _add_result(label: str, lat: float, lng: float, poi_id: int | None = None, category: str | None = None):
        key = _normalize_vn(label)
        if key in seen_labels:
            return
        seen_labels.add(key)
        item: dict = {"label": label, "lat": float(lat), "lng": float(lng)}
        if poi_id is not None:
            item["poi_id"] = int(poi_id)
        if category:
            item["category"] = category
        results.append(item)

    # 1. Địa danh lớn & trường đại học
    for lm in HCMC_LANDMARKS:
        if q_norm in _normalize_vn(lm["label"]):
            _add_result(lm["label"], lm["lat"], lm["lng"])

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
    limit: int = 30,
) -> list[dict]:
    """Tìm địa điểm trong khung nhìn bản đồ; tự nới bán kính quanh tâm nếu vùng đang zoom ít kết quả."""
    q_clean = query.strip()
    q_norm = _normalize_vn(q_clean)
    cat_intent = _detect_category_intent(q_norm)
    center_lat = (south + north) / 2.0
    center_lng = (west + east) / 2.0

    results: list[dict] = []
    seen_keys: set[str] = set()

    def _push_place(
        poi_id: int,
        name: str,
        address: str,
        street: str,
        lat: float,
        lng: float,
        max_radius_km: float = 4.5,
        sub_type: str = "",
        opening_hours: str | None = None,
        cuisine: str | None = None,
    ):
        dist_km = _haversine_km(center_lat, center_lng, float(lat), float(lng))
        if dist_km > max_radius_km:
            return
        name_clean = name.strip()
        if not name_clean or _normalize_vn(name_clean) == q_norm:
            return
        key = f"{_normalize_vn(name_clean)}|{round(lat, 3)}|{round(lng, 3)}"
        if key in seen_keys:
            return
        seen_keys.add(key)

        results.append({
            "poi_id": poi_id,
            "name": name_clean,
            "amenity": cat_intent or "custom",
            "category": cat_intent or "custom",
            "sub_type": sub_type or cat_intent or "custom",
            "street": street,
            "address": address or street,
            "opening_hours": opening_hours,
            "cuisine": cuisine,
            "lat": float(lat),
            "lng": float(lng),
            "f_sum": 0.0,
            "f_max": 0.0,
            "person_times": [],
            "distance_km": round(dist_km, 2),
        })

    # 1. Tìm trong kho 3,271 POI nội bộ (lọc theo từ khóa / danh mục, lấy trong bán kính 4.5km quanh tâm bản đồ)
    df = engine.df_pois
    if not hasattr(engine, "_poi_norm_series"):
        engine._poi_norm_series = (
            engine.df_pois["name"].astype(str) + " " + engine.df_pois["address"].astype(str)
        ).apply(_normalize_vn)

    cat_col = df["category"] if "category" in df.columns else df["amenity"]
    if cat_intent:
        mask = (cat_col == cat_intent) | engine._poi_norm_series.str.contains(q_norm, regex=False, na=False)
        sub = df[mask].copy()
    elif q_norm and q_norm != "all":
        sub = df[engine._poi_norm_series.str.contains(q_norm, regex=False, na=False)].copy()
    else:
        sub = df.copy()

    if not sub.empty:
        sub["_dist_km"] = np.hypot(
            (sub["lat"] - center_lat) * 111.0,
            (sub["lng"] - center_lng) * 109.0,
        )
        sub = sub[sub["_dist_km"] <= 4.5].sort_values("_dist_km")
        for _, row in sub.head(limit).iterrows():
            oh = str(row.get("opening_hours", ""))
            cu = str(row.get("cuisine", ""))
            _push_place(
                poi_id=int(row["poi_id"]),
                name=str(row["name"]),
                address=str(row.get("address") or row.get("street") or ""),
                street=str(row.get("street") or ""),
                lat=float(row["lat"]),
                lng=float(row["lng"]),
                max_radius_km=4.5,
                sub_type=str(row.get("sub_type") or row.get("amenity") or ""),
                opening_hours=None if oh in ("", "nan", "None") else oh,
                cuisine=None if cu in ("", "nan", "None") else cu,
            )

    # 2. Bổ sung thêm từ ArcGIS & Photon xếp hạng theo độ gần tâm bản đồ (bán kính 4.5km)
    if len(results) < 10 and q_norm and q_norm != "all":
        area_ctx = await reverse_geocode(center_lat, center_lng, engine)
        district = area_ctx.split(",")[-1].strip() if "," in area_ctx else "Hồ Chí Minh"
        wide_extent = f"{center_lng - 0.045},{center_lat - 0.045},{center_lng + 0.045},{center_lat + 0.045}"

        alt_query = "sân bóng" if cat_intent == "sports" else q_clean
        async with httpx.AsyncClient(headers=HEADERS) as client:
            c1, c2, photon_feats = await asyncio.gather(
                _query_arcgis_candidates(client, f"{q_clean}, {district}, Hồ Chí Minh", center_lat, center_lng, wide_extent),
                _query_arcgis_candidates(client, f"{alt_query}, Hồ Chí Minh", center_lat, center_lng, wide_extent),
                _query_photon_candidates(client, f"{alt_query} {district}", center_lat, center_lng),
            )

        idx_counter = 100
        for cand in [*c1, *c2]:
            loc = cand.get("location", {})
            lat, lng = loc.get("y"), loc.get("x")
            if lat is None or lng is None:
                continue
            attrs = cand.get("attributes", {})
            full_addr = (
                cand.get("address", "")
                .replace(", Thành phố Hồ Chí Minh", "")
                .replace(", Hồ Chí Minh", "")
                .replace(", Việt Nam", "")
            )
            place_name = (attrs.get("PlaceName") or full_addr.split(",")[0]).strip()
            street_label = engine.get_nearest_street_label(float(lat), float(lng))
            _push_place(
                poi_id=-idx_counter,
                name=place_name,
                address=full_addr or street_label,
                street=street_label,
                lat=float(lat),
                lng=float(lng),
                max_radius_km=4.5,
                sub_type=attrs.get("Type") or cat_intent or "custom",
            )
            idx_counter += 1

        for feat in photon_feats:
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            p_name = props.get("name")
            if not p_name:
                continue
            p_street = props.get("street") or engine.get_nearest_street_label(coords[1], coords[0])
            p_dist = props.get("district") or district
            _push_place(
                poi_id=-idx_counter,
                name=str(p_name),
                address=f"{p_street}, {p_dist}",
                street=str(p_street),
                lat=float(coords[1]),
                lng=float(coords[0]),
                max_radius_km=4.5,
            )
            idx_counter += 1

    results.sort(key=lambda x: x.get("distance_km", 99.0))
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