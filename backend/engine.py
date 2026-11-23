import heapq
import time
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
from scipy.sparse.csgraph import dijkstra as scipy_dijkstra
from scipy.spatial import cKDTree


class MeetingPointEngine:
    def __init__(self, adj_path: str, meta_path: str, poi_path: str):
        t0 = time.perf_counter()
        # 1. Nạp ma trận đồ thị và tọa độ đỉnh
        self.adj_matrix = load_npz(adj_path)
        meta = np.load(meta_path)
        self.coords = meta["coords"]  # Shape (N, 2) -> [lat, lng]
        self.num_nodes = self.adj_matrix.shape[0]
        self.tree = cKDTree(self.coords)

        # 2. Chuẩn bị danh sách kề & thông số cạnh cho Time-Dependent & Wavefront
        self.rows, self.cols = self.adj_matrix.nonzero()
        self.base_weights = self.adj_matrix.data

        lat_u, lng_u = self.coords[self.rows, 0], self.coords[self.rows, 1]
        lat_v, lng_v = self.coords[self.cols, 0], self.coords[self.cols, 1]
        dy = (lat_v - lat_u) * 111320.0
        dx = (lng_v - lng_u) * 111320.0 * np.cos(np.radians((lat_u + lat_v) / 2.0))
        dist_m = np.sqrt(dx**2 + dy**2)
        self.is_major_road = (dist_m / np.maximum(self.base_weights, 0.1)) > 5.5

        self.adj_list = [[] for _ in range(self.num_nodes)]
        for edge_idx, (u, v, w) in enumerate(zip(self.rows, self.cols, self.base_weights)):
            self.adj_list[int(u)].append((int(v), float(w), edge_idx))

        # 3. Nạp và làm sạch dữ liệu POI (khử trùng lặp theo tên + đỉnh gần nhất)
        df_pois = pd.read_csv(poi_path)
        dists_deg, nearest_nodes = self.tree.query(df_pois[["lat", "lng"]].values)
        df_pois["node_idx"] = nearest_nodes
        df_pois["snap_dist_m"] = dists_deg * 110500.0
        df_pois = df_pois[df_pois["snap_dist_m"] <= 150.0].copy()
        df_pois = df_pois.drop_duplicates(subset=["name", "node_idx"]).reset_index(drop=True)
        self.df_pois = df_pois

        print(f"[Engine Ready] Đã nạp {self.num_nodes:,} đỉnh & {len(self.df_pois):,} POIs trong {(time.perf_counter()-t0)*1000:.1f} ms")

    def _get_traffic_multiplier(self, hour_float: float, is_major: bool) -> float:
        is_rush = (7.0 <= hour_float <= 9.0) or (16.5 <= hour_float <= 19.0)
        is_mod = (11.5 <= hour_float <= 13.5) or (19.0 < hour_float <= 21.0)
        if is_rush:
            return 1.85 if is_major else 1.25
        elif is_mod:
            return 1.30 if is_major else 1.10
        return 1.00

    def _dijkstra_with_parent(self, start_node: int, depart_hour: float | None = None):
        """Chạy Dijkstra trả về vector thời gian (giây) và mảng truy vết đường đi."""
        dist = np.full(self.num_nodes, np.inf, dtype=np.float64)
        parent = np.full(self.num_nodes, -1, dtype=np.int32)
        dist[start_node] = 0.0
        pq = [(0.0, start_node)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            cur_hour = ((depart_hour + d / 3600.0) % 24.0) if depart_hour is not None else 10.0
            for v, base_w, edge_idx in self.adj_list[u]:
                w = base_w * self._get_traffic_multiplier(cur_hour, self.is_major_road[edge_idx]) if depart_hour is not None else base_w
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    parent[v] = u
                    heapq.heappush(pq, (nd, v))
        return dist, parent

    def _reconstruct_path_coords(self, parent: np.ndarray, start_node: int, target_node: int) -> list:
        """Truy vết mảng parent để xuất danh sách tọa độ [lng, lat] chuẩn GeoJSON."""
        path = []
        curr = int(target_node)
        while curr != -1:
            lat, lng = self.coords[curr]
            path.append([float(lng), float(lat)])  # GeoJSON dùng thứ tự [lng, lat]
            if curr == start_node:
                break
            curr = int(parent[curr])
        path.reverse()
        return path

    def solve(self, people: list[dict], alpha: float = 0.5, depart_hour: float | None = None, amenity_filter: str = "all"):
        """
        people: [{"name": "An", "lat": 10.7725, "lng": 106.6980}, ...]
        alpha: 0.0 (thuần tổng thời gian) -> 1.0 (thuần công bằng Minimax)
        depart_hour: None (giờ bình thường) hoặc số thực (vd 17.5 = 17:30)
        """
        t0 = time.perf_counter()
        k = len(people)
        sources = [int(self.tree.query([p["lat"], p["lng"]])[1]) for p in people]

        # 1. Tính trường thời gian và mảng truy vết cho từng người
        T_sec = np.zeros((k, self.num_nodes), dtype=np.float64)
        parents = []
        for i, s in enumerate(sources):
            dist_i, parent_i = self._dijkstra_with_parent(s, depart_hour)
            T_sec[i] = dist_i
            parents.append(parent_i)

        T_min = T_sec / 60.0
        F_sum = np.sum(T_min, axis=0)
        F_max = np.max(T_min, axis=0)

        # 2. Tìm đỉnh tối ưu theo tham số thanh trượt alpha
        cost_all = (1.0 - alpha) * (F_sum / k) + alpha * F_max
        best_node = int(np.argmin(cost_all))
        best_lat, best_lng = self.coords[best_node]

        # 3. Truy vết tuyến đường chi tiết (GeoJSON LineString) từ từng người tới best_node
        routes_geojson = []
        times_per_person = []
        for i, p in enumerate(people):
            path_coords = self._reconstruct_path_coords(parents[i], sources[i], best_node)
            t_val = round(float(T_min[i, best_node]), 1)
            times_per_person.append({
                "name": p["name"],
                "minutes": t_val,
                "snapped_coord": [float(self.coords[sources[i], 1]), float(self.coords[sources[i], 0])]
            })
            routes_geojson.append({
                "type": "Feature",
                "properties": {"person_index": i, "name": p["name"], "minutes": t_val},
                "geometry": {"type": "LineString", "coordinates": path_coords}
            })

        # 4. Xếp hạng Top 15 POIs thật quanh khu vực tối ưu
        poi_nodes = self.df_pois["node_idx"].values
        T_pois = T_min[:, poi_nodes]
        poi_f_sum = np.sum(T_pois, axis=0)
        poi_f_max = np.max(T_pois, axis=0)
        poi_cost = (1.0 - alpha) * (poi_f_sum / k) + alpha * poi_f_max

        df_res = self.df_pois.copy()
        df_res["f_sum"] = np.round(poi_f_sum, 1)
        df_res["f_max"] = np.round(poi_f_max, 1)
        df_res["score"] = np.round(poi_cost, 2)
        for i, p in enumerate(people):
            df_res[f"p_{i}"] = np.round(T_pois[i], 1)

        if amenity_filter != "all":
            df_res = df_res[df_res["amenity"] == amenity_filter]

        top_df = df_res.sort_values("score").head(15)
        top_pois = []
        for _, row in top_df.iterrows():
            person_times = {people[i]["name"]: float(row[f"p_{i}"]) for i in range(k)}
            top_pois.append({
                "name": row["name"],
                "amenity": row["amenity"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "f_sum": float(row["f_sum"]),
                "f_max": float(row["f_max"]),
                "score": float(row["score"]),
                "times": person_times
            })

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "compute_ms": round(elapsed_ms, 2),
            "optimum": {
                "node_idx": best_node,
                "lat": float(best_lat),
                "lng": float(best_lng),
                "f_sum": round(float(F_sum[best_node]), 1),
                "f_max": round(float(F_max[best_node]), 1),
            },
            "times_per_person": times_per_person,
            "routes": {"type": "FeatureCollection", "features": routes_geojson},
            "top_pois": top_pois
        }

    def compute_wavefront_edges(self, people: list[dict], max_minutes: float = 15.0):
        """
        Chạy thuật toán nước loang đồng bộ A4 và xuất toàn bộ các cạnh đường được loang tới
        kèm mốc thời gian t (phút) và person_index để frontend chạy animation phát sáng!
        """
        k = len(people)
        sources = [int(self.tree.query([p["lat"], p["lng"]])[1]) for p in people]
        max_sec = max_minutes * 60.0

        T = np.full((k, self.num_nodes), np.inf, dtype=np.float64)
        visited_count = np.zeros(self.num_nodes, dtype=np.int32)
        pq = []
        for i, s in enumerate(sources):
            T[i, s] = 0.0
            heapq.heappush(pq, (0.0, i, s, -1))  # (thời_gian, người_i, đỉnh_u, đỉnh_cha)

        features = []
        meeting_node = -1
        meeting_time_min = None

        while pq:
            t, p_idx, u, parent_u = heapq.heappop(pq)
            if t > T[p_idx, u] or t > max_sec:
                continue

            # Ghi lại đoạn đường vừa loang tới đỉnh u
            if parent_u != -1:
                lat1, lng1 = self.coords[parent_u]
                lat2, lng2 = self.coords[u]
                features.append({
                    "type": "Feature",
                    "properties": {
                        "person": p_idx,
                        "t": round(t / 60.0, 2)  # Mốc thời gian loang tới (phút)
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[float(lng1), float(lat1)], [float(lng2), float(lat2)]]
                    }
                })

            visited_count[u] += 1
            if visited_count[u] == k and meeting_node == -1:
                meeting_node = u
                meeting_time_min = round(t / 60.0, 2)
                # Tiếp tục loang thêm một chút (hoặc dừng ngay tùy ý); ở đây dừng ngay tại điểm gặp Minimax
                break

            for v, w, _ in self.adj_list[u]:
                nt = t + w
                if nt < T[p_idx, v]:
                    T[p_idx, v] = nt
                    heapq.heappush(pq, (nt, p_idx, v, u))

        return {
            "meeting_node": meeting_node,
            "meeting_time_min": meeting_time_min,
            "total_edges": len(features),
            "geojson": {"type": "FeatureCollection", "features": features}
        }