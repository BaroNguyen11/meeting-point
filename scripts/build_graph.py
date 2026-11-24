import json
import os
import time
import unicodedata
import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse import csr_matrix, save_npz

# ==============================================================================
# 1. CẤU HÌNH MẠNG, CACHE & MIRROR OVERPASS
# ==============================================================================
# Ưu tiên các mirror phản hồi nhanh và ổn định nhất lên đầu
OVERPASS_MIRRORS = [
    "https://z.overpass-api.de/api",
    "https://overpass-api.de/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
    "https://lz4.overpass-api.de/api",
]

ox.settings.use_cache = True
ox.settings.cache_folder = "cache"
ox.settings.log_console = False
ox.settings.overpass_rate_limit = False
ox.settings.requests_timeout = 90

# ==============================================================================
# 2. PHẠM VI BẢN ĐỒ & LƯỚI CHIA Ô (4x4 = 16 Ô NHỎ)
# ==============================================================================
# Bao phủ toàn bộ vùng lõi & các quận trung tâm TP.HCM:
# Q1, Q3, Q4, Q5, Q6, Q7 (Phú Mỹ Hưng), Q8, Q10, Q11, Bình Thạnh, Phú Nhuận,
# Tân Bình, Tân Phú, Gò Vấp (IUH) và Thảo Điền / An Phú (Thủ Đức).
BBOX_HCMC_METRO = (106.5800, 10.6400, 106.8150, 10.8900)
GRID_COLS = 5
GRID_ROWS = 5

# ==============================================================================
# 3. THAM SỐ VẬT LÝ MẠNG LƯỚI XE MÁY ĐÔ THỊ TP.HCM
# ==============================================================================
# Vận tốc thực tế (km/h) theo cấp đường OpenStreetMap trong điều kiện bình thường
MOTO_SPEED_KMH = {
    "trunk": 36.0,
    "trunk_link": 28.0,
    "primary": 32.0,
    "primary_link": 25.0,
    "secondary": 28.0,
    "secondary_link": 22.0,
    "tertiary": 24.0,
    "tertiary_link": 20.0,
    "unclassified": 20.0,
    "residential": 18.0,
    "living_street": 15.0,
    "service": 14.0,
}

# Các trục đường chính dễ chịu ảnh hưởng nặng vào giờ cao điểm (17:30)
MAJOR_HIGHWAYS = {
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
}

# Các loại đường chỉ dành cho người đi bộ / công trình chưa hoàn thiện (loại bỏ)
NON_MOTO_HIGHWAYS = {
    "footway", "steps", "pedestrian", "cycleway", "path",
    "corridor", "elevator", "track", "bridleway",
    "proposed", "construction", "raceway",
}

# ==============================================================================
# 4. BỘ NHÃN ĐỊA ĐIỂM (POI) & TỪ KHÓA PHÂN LOẠI TIẾNG VIỆT
# ==============================================================================
OSM_POI_TAGS = {
    "amenity": [
        "cafe", "restaurant", "fast_food", "food_court", "ice_cream",
        "pub", "biergarten", "cinema", "karaoke_box",
    ],
    "leisure": [
        "pitch", "sports_centre", "stadium", "fitness_centre",
        "swimming_pool", "park", "bowling_alley",
    ],
    "shop": ["mall", "department_store"],
    "tourism": ["museum", "attraction"],
}

SPORTS_KEYWORDS = (
    "san bong", "san da banh", "bong da", "cau long", "pickleball",
    "tennis", "bong ro", "ho boi", "be boi", "gym", "fitness",
    "the thao", "nha thi dau", "svd", "san van dong",
)
CAFE_KEYWORDS = (
    "cafe", "ca phe", "coffee", "tra sua", "tea", "matcha",
    "espresso", "roastery", "bakery", "tiem banh", "kem",
)
FOOD_KEYWORDS = (
    "pho", "bun", "com", "hu tieu", "banh mi", "lau", "nuong",
    "quan an", "nha hang", "ga ran", "bo ne", "oc", "hai san",
    "dimsum", "sushi", "pizza", "bbq", "buffet", "chay",
)


# ==============================================================================
# HÀM HỖ TRỢ XỬ LÝ CHUỖI & TẢI DỮ LIỆU
# ==============================================================================
def normalize_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def clean_osm_name(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    if isinstance(val, list):
        unique_names = list(dict.fromkeys(str(x).strip() for x in val if x))
        return " / ".join(unique_names)
    return str(val).strip()


def first_tag_str(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    if isinstance(val, list):
        return str(val[0]).strip() if val else ""
    return str(val).strip()


def build_grid_tiles(bbox: tuple[float, float, float, float], cols: int, rows: int) -> list[tuple[float, float, float, float]]:
    west, south, east, north = bbox
    lons = np.linspace(west, east, cols + 1)
    lats = np.linspace(south, north, rows + 1)
    tiles = []
    for r in range(rows):
        for c in range(cols):
            tiles.append((float(lons[c]), float(lats[r]), float(lons[c + 1]), float(lats[r + 1])))
    return tiles


def fetch_with_mirror_fallback(func, *args, **kwargs):
    last_err = None
    for mirror in OVERPASS_MIRRORS:
        try:
            ox.settings.overpass_url = mirror
            return func(*args, **kwargs)
        except Exception as err:
            last_err = err
            host = mirror.split("//")[1].split("/")[0]
            print(f"      ! Mirror {host} quá tải, chuyển mirror kế tiếp...")
            time.sleep(1.0)
    raise RuntimeError(f"Tất cả mirror Overpass đều thất bại: {last_err}")


def classify_poi(row: pd.Series, clean_name: str) -> tuple[str, str]:
    """Chuẩn hóa địa điểm về 4 nhóm chính: cafe, restaurant, sports, entertainment."""
    name_norm = normalize_vn(clean_name)
    amenity_tag = first_tag_str(row.get("amenity"))
    leisure_tag = first_tag_str(row.get("leisure"))
    shop_tag = first_tag_str(row.get("shop"))
    tourism_tag = first_tag_str(row.get("tourism"))
    sport_tag = first_tag_str(row.get("sport"))

    # 1. Nhóm Thể thao / Sân bóng
    if leisure_tag in {"pitch", "sports_centre", "stadium", "fitness_centre", "swimming_pool"} or any(
        kw in name_norm for kw in SPORTS_KEYWORDS
    ):
        sub = sport_tag or leisure_tag or "sports"
        return "sports", sub

    # 2. Nhóm Giải trí / TTTM / Công viên / Rạp phim
    if (
        amenity_tag in {"cinema", "karaoke_box"}
        or leisure_tag in {"park", "bowling_alley"}
        or shop_tag in {"mall", "department_store"}
        or tourism_tag in {"museum", "attraction"}
    ):
        sub = amenity_tag or leisure_tag or shop_tag or tourism_tag or "entertainment"
        return "entertainment", sub

    # 3. Nhóm Quán ăn vs Cà phê (ưu tiên từ khóa tiếng Việt để sửa nhãn gắn nhầm trên OSM)
    if any(kw in name_norm for kw in FOOD_KEYWORDS):
        return "restaurant", amenity_tag or "restaurant"

    if amenity_tag in {"cafe", "ice_cream"} or any(kw in name_norm for kw in CAFE_KEYWORDS):
        return "cafe", amenity_tag or "cafe"

    return "restaurant", amenity_tag or "restaurant"


# ==============================================================================
# PIPELINE XÂY DỰNG DỮ LIỆU CHÍNH
# ==============================================================================
def build_hcmc_metro_dataset():
    t0 = time.perf_counter()
    os.makedirs("data", exist_ok=True)
    tiles = build_grid_tiles(BBOX_HCMC_METRO, cols=GRID_COLS, rows=GRID_ROWS)
    total_tiles = len(tiles)

    # --------------------------------------------------------------------------
    # BƯỚC 1: TẢI & GHÉP MẠNG LƯỚI ĐƯỜNG XE MÁY TOÀN NỘI THÀNH
    # --------------------------------------------------------------------------
    print(f"1/4 Đang tải mạng lưới giao thông TP.HCM ({total_tiles} ô lưới nối cạnh liền mạch)...")
    raw_graphs = []
    for idx, tile_bbox in enumerate(tiles, start=1):
        t_tile = time.perf_counter()
        g_tile = fetch_with_mirror_fallback(
            ox.graph_from_bbox,
            bbox=tile_bbox,
            network_type="all",
            simplify=False,
            retain_all=True,
            truncate_by_edge=True,
        )
        raw_graphs.append(g_tile)
        print(f"    -> Ô [{idx:02d}/{total_tiles}] xong ({g_tile.number_of_nodes():,} đỉnh raw, {time.perf_counter() - t_tile:.1f}s)")

    print("    -> Đang ghép nối các ô lưới, lọc đường xe máy & rút gọn nút giao...")
    G_composed = nx.compose_all(raw_graphs)

    # Loại bỏ đường đi bộ, cầu thang, đường cấm xe máy
    edges_to_drop = []
    for u, v, k, data in G_composed.edges(keys=True, data=True):
        hw = first_tag_str(data.get("highway"))
        moto_access = first_tag_str(data.get("motorcycle"))
        motor_access = first_tag_str(data.get("motor_vehicle"))
        if hw in NON_MOTO_HIGHWAYS or moto_access == "no" or motor_access == "no":
            edges_to_drop.append((u, v, k))

    G_composed.remove_edges_from(edges_to_drop)
    G_composed.remove_nodes_from(list(nx.isolates(G_composed)))

    # Rút gọn các đỉnh trung gian trên đoạn đường thẳng, chỉ giữ lại ngã ba/ngã tư
    G = ox.simplify_graph(G_composed)

    # Giữ thành phần liên thông mạnh lớn nhất để đảm bảo mọi điểm đều đi tới nhau được
    largest_scc = max(nx.strongly_connected_components(G), key=len)
    G = G.subgraph(largest_scc).copy()
    G = nx.convert_node_labels_to_integers(G, first_label=0, ordering="default")

    num_nodes = G.number_of_nodes()
    print(f"    -> Đồ thị liên thông toàn nội thành: {num_nodes:,} nút giao, {G.number_of_edges():,} cạnh.")
    if num_nodes < 25000:
        raise RuntimeError(f"Cảnh báo: Đồ thị chỉ có {num_nodes} đỉnh — kiểm tra lại kết nối lưới!")

    # --------------------------------------------------------------------------
    # BƯỚC 2: XÂY DỰNG MA TRẬN KỀ & SIÊU DỮ LIỆU ĐƯỜNG PHỐ (.NPZ)
    # --------------------------------------------------------------------------
    coords = np.zeros((num_nodes, 2), dtype=np.float64)
    node_streets: list[set[str]] = [set() for _ in range(num_nodes)]

    for u, data in G.nodes(data=True):
        coords[u, 0] = data["y"]
        coords[u, 1] = data["x"]

    # Gộp các cạnh song song giữa cùng cặp (u, v) bằng cách giữ cạnh nhanh nhất
    best_edges: dict[tuple[int, int], tuple[float, float, bool, str]] = {}
    for u, v, data in G.edges(data=True):
        if u == v:
            continue
        length_m = float(data.get("length", 10.0))
        hw = first_tag_str(data.get("highway"))
        speed_kmh = MOTO_SPEED_KMH.get(hw, 20.0)
        travel_sec = (length_m / (speed_kmh / 3.6)) + 3.0
        is_major = hw in MAJOR_HIGHWAYS
        st_name = clean_osm_name(data.get("name"))

        if st_name:
            node_streets[u].add(st_name)
            node_streets[v].add(st_name)

        prev = best_edges.get((u, v))
        if prev is None or travel_sec < prev[0]:
            best_edges[(u, v)] = (travel_sec, length_m, is_major, st_name)

    sorted_pairs = sorted(best_edges.keys())
    rows = [u for u, _ in sorted_pairs]
    cols = [v for _, v in sorted_pairs]
    weights = [best_edges[p][0] for p in sorted_pairs]
    edge_lengths_m = np.array([best_edges[p][1] for p in sorted_pairs], dtype=np.float32)
    edge_is_major = np.array([best_edges[p][2] for p in sorted_pairs], dtype=bool)
    edge_names = np.array([best_edges[p][3] for p in sorted_pairs], dtype=object)

    node_names = np.array(
        [" – ".join(sorted(streets)[:2]) if streets else "Đường nội bộ TP.HCM" for streets in node_streets],
        dtype=object,
    )

    adj_matrix = csr_matrix((weights, (rows, cols)), shape=(num_nodes, num_nodes), dtype=np.float64)
    save_npz("data/hcm_metro_moto_adj.npz", adj_matrix)
    np.savez_compressed(
        "data/hcm_metro_moto_meta.npz",
        coords=coords,
        node_names=node_names,
        edge_lengths_m=edge_lengths_m,
        edge_is_major=edge_is_major,
        edge_names=edge_names,
        bbox=np.array(BBOX_HCMC_METRO, dtype=np.float64),
    )
    print(f"2/4 Đã lưu ma trận kề ({adj_matrix.nnz:,} cạnh duy nhất) & siêu dữ liệu đường phố.")

    # --------------------------------------------------------------------------
    # BƯỚC 3: TRÍCH XUẤT & GÁN ĐỊA CHỈ THẬT CHO TOÀN BỘ ĐỊA ĐIỂM (POI)
    # --------------------------------------------------------------------------
    print(f"3/4 Đang tải toàn bộ Quán ăn, Cà phê, Sân thể thao & Giải trí trên {total_tiles} ô lưới...")
    poi_frames = []
    for idx, tile_bbox in enumerate(tiles, start=1):
        try:
            df_tile = fetch_with_mirror_fallback(ox.features_from_bbox, bbox=tile_bbox, tags=OSM_POI_TAGS)
            poi_frames.append(df_tile)
            print(f"    -> POI ô [{idx:02d}/{total_tiles}] xong ({len(df_tile):,} điểm)")
        except Exception as err:
            print(f"    -> Bỏ qua POI ô [{idx:02d}/{total_tiles}]: {err}")

    pois_gdf = pd.concat(poi_frames)
    pois_gdf = pois_gdf[~pois_gdf.index.duplicated(keep="first")]
    pois_gdf = pois_gdf[pois_gdf["name"].notna()].copy()

    # Chuyển về hệ chiếu UTM Zone 48N (mét) để tính tâm hình học & nối tên đường chính xác
    pois_utm = pois_gdf.to_crs("EPSG:32648")
    centroids_wgs84 = pois_utm.geometry.centroid.to_crs("EPSG:4326")
    pois_gdf["lat"] = centroids_wgs84.y
    pois_gdf["lng"] = centroids_wgs84.x
    pois_gdf["geometry"] = pois_utm.geometry.centroid

    _, edges_gdf = ox.graph_to_gdfs(G)
    edges_gdf["clean_street"] = edges_gdf["name"].apply(clean_osm_name)
    named_edges_utm = edges_gdf[edges_gdf["clean_street"] != ""][["clean_street", "geometry"]].to_crs("EPSG:32648")

    # Mở rộng bán kính tìm đường lên 120m để không bỏ sót sân vận động / công viên lớn
    joined = gpd.sjoin_nearest(pois_gdf, named_edges_utm, how="left", max_distance=120.0)
    joined = joined[~joined.index.duplicated(keep="first")]

    records = []
    for _, row in joined.iterrows():
        raw_name = clean_osm_name(row.get("name"))
        if not raw_name or len(raw_name) < 2:
            continue

        category, sub_type = classify_poi(row, raw_name)
        house_num = clean_osm_name(row.get("addr:housenumber"))
        osm_street = clean_osm_name(row.get("addr:street"))
        nearest_street = clean_osm_name(row.get("clean_street"))
        final_street = osm_street if osm_street else nearest_street

        if not final_street:
            continue

        full_address = f"{house_num} {final_street}".strip() if house_num else final_street
        lat_val = round(float(row["lat"]), 6)
        lng_val = round(float(row["lng"]), 6)

        # Khóa chống trùng thông minh theo ô 100m (giữ được nhiều chi nhánh trên cùng 1 đường dài)
        spatial_bucket = f"{round(lat_val, 3)}_{round(lng_val, 3)}"
        dedup_key = f"{normalize_vn(raw_name)}|{spatial_bucket}"

        records.append({
            "dedup_key": dedup_key,
            "name": raw_name,
            "amenity": category,       # Giữ tương thích ngược với GraphEngine hiện tại
            "category": category,      # Nhóm chuẩn: cafe | restaurant | sports | entertainment
            "sub_type": sub_type,      # Chi tiết: pitch | cinema | mall | park | cafe | restaurant...
            "street": final_street,
            "address": full_address,
            "opening_hours": clean_osm_name(row.get("opening_hours")),
            "cuisine": clean_osm_name(row.get("cuisine")),
            "phone": clean_osm_name(row.get("phone") or row.get("contact:phone")),
            "website": clean_osm_name(row.get("website") or row.get("contact:website")),
            "lat": lat_val,
            "lng": lng_val,
        })

    df_pois = (
        pd.DataFrame(records)
        .drop_duplicates(subset=["dedup_key"])
        .drop(columns=["dedup_key"])
        .reset_index(drop=True)
    )
    df_pois.to_csv("data/hcm_metro_pois.csv", index=False, encoding="utf-8-sig")

    # --------------------------------------------------------------------------
    # BƯỚC 4: XUẤT BÁO CÁO TỔNG HỢP DATASET
    # --------------------------------------------------------------------------
    elapsed = round(time.perf_counter() - t0, 1)
    category_counts = df_pois["category"].value_counts().to_dict()
    manifest = {
        "bbox": list(BBOX_HCMC_METRO),
        "grid": f"{GRID_COLS}x{GRID_ROWS}",
        "nodes": int(num_nodes),
        "directed_edges": int(adj_matrix.nnz),
        "major_road_edges": int(np.sum(edge_is_major)),
        "local_alley_edges": int(np.sum(~edge_is_major)),
        "total_pois": int(len(df_pois)),
        "pois_by_category": category_counts,
        "build_seconds": elapsed,
    }
    with open("data/dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"4/4 Hoàn tất trong {elapsed}s! Đã xuất {len(df_pois):,} địa điểm tại data/hcm_metro_pois.csv:")
    for cat, cnt in category_counts.items():
        print(f"    - {cat}: {cnt:,} địa điểm")


if __name__ == "__main__":
    build_hcmc_metro_dataset()