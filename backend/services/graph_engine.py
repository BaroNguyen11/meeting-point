import time
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, load_npz
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree


class GraphEngine:
    def __init__(self, adj_path: str, meta_path: str, poi_path: str):
        t0 = time.perf_counter()
        self.adj_matrix = load_npz(adj_path).tocsr()
        meta = np.load(meta_path, allow_pickle=True)

        self.coords = meta["coords"]  # [lat, lng]
        self.num_nodes = self.adj_matrix.shape[0]
        self.node_names = (
            meta["node_names"]
            if "node_names" in meta
            else np.array(["Đường nội thành TP.HCM"] * self.num_nodes, dtype=object)
        )

        self.rows, self.cols = self.adj_matrix.nonzero()
        self.base_weights = self.adj_matrix.data

        # Đọc thông tin cấp đường & chiều dài cạnh từ file meta mới
        if "edge_is_major" in meta:
            self.is_major_road = meta["edge_is_major"].astype(bool)
        else:
            lat_u, lng_u = self.coords[self.rows, 0], self.coords[self.rows, 1]
            lat_v, lng_v = self.coords[self.cols, 0], self.coords[self.cols, 1]
            dist_m = np.hypot((lat_v - lat_u) * 111320.0, (lng_v - lng_u) * 109300.0)
            self.is_major_road = (dist_m / np.maximum(self.base_weights, 0.1)) > 5.5

        if "edge_lengths_m" in meta:
            self.edge_lengths_m = meta["edge_lengths_m"].astype(np.float64)
        else:
            lat_u, lng_u = self.coords[self.rows, 0], self.coords[self.rows, 1]
            lat_v, lng_v = self.coords[self.cols, 0], self.coords[self.cols, 1]
            self.edge_lengths_m = np.hypot((lat_v - lat_u) * 111320.0, (lng_v - lng_u) * 109300.0)

        self.edge_len_lookup = {
            (int(u), int(v)): float(l)
            for u, v, l in zip(self.rows, self.cols, self.edge_lengths_m)
        }

        # Tiền tính toán ma trận giờ cao điểm (17:30): đường trục chính x1.85, hẻm/đường nhánh x1.25
        rush_multipliers = np.where(self.is_major_road, 1.85, 1.25)
        self.adj_matrix_rush = csr_matrix(
            (self.base_weights * rush_multipliers, (self.rows, self.cols)),
            shape=(self.num_nodes, self.num_nodes),
            dtype=np.float64,
        )

        self.tree = cKDTree(self.coords)

        # Nạp danh mục địa điểm (Cà phê, Quán ăn, Sân thể thao, Giải trí)
        df_pois = pd.read_csv(poi_path)
        dists_deg, nearest_nodes = self.tree.query(df_pois[["lat", "lng"]].values)
        df_pois["node_idx"] = nearest_nodes
        df_pois["snap_dist_m"] = dists_deg * 110500.0
        df_pois = df_pois[df_pois["snap_dist_m"] <= 250.0].copy()

        if "category" not in df_pois.columns:
            df_pois["category"] = df_pois["amenity"]
        if "sub_type" not in df_pois.columns:
            df_pois["sub_type"] = df_pois["category"]

        for col in ("street", "address", "opening_hours", "cuisine", "phone", "website", "category", "sub_type"):
            if col not in df_pois.columns:
                df_pois[col] = ""
            df_pois[col] = df_pois[col].fillna("").astype(str)

        df_pois = df_pois.reset_index(drop=True)
        df_pois["poi_id"] = df_pois.index.astype(int)
        self.df_pois = df_pois
        print(
            f"[GraphEngine] Sẵn sàng {self.num_nodes:,} nút giao, "
            f"{self.adj_matrix.nnz:,} cạnh & {len(self.df_pois):,} địa điểm "
            f"({(time.perf_counter() - t0) * 1000:.1f} ms)"
        )

    def get_nearest_street_label(self, lat: float, lng: float) -> str:
        _, node_idx = self.tree.query([lat, lng])
        return str(self.node_names[int(node_idx)])

    def _select_graph_matrix(self, depart_hour: float | None) -> csr_matrix:
        if depart_hour is None:
            return self.adj_matrix
        is_rush = (7.0 <= depart_hour <= 9.0) or (16.5 <= depart_hour <= 19.0)
        return self.adj_matrix_rush if is_rush else self.adj_matrix

    def _run_multi_source_dijkstra(self, sources: list[int], depart_hour: float | None, limit_sec: float | None = None):
        matrix = self._select_graph_matrix(depart_hour)
        kwargs = {
            "csgraph": matrix,
            "directed": True,
            "indices": sources,
            "return_predecessors": True,
        }
        if limit_sec is not None:
            kwargs["limit"] = limit_sec
        return dijkstra(**kwargs)

    def _reconstruct_path_and_km(self, pred_row: np.ndarray, start_node: int, target_node: int) -> tuple[list[list[float]], float]:
        node_seq = []
        curr = int(target_node)
        visited_guard = 0
        while curr >= 0 and visited_guard < self.num_nodes:
            node_seq.append(curr)
            if curr == start_node:
                break
            curr = int(pred_row[curr])
            visited_guard += 1
        node_seq.reverse()

        coords_list = []
        total_m = 0.0
        for idx, u in enumerate(node_seq):
            lat, lng = self.coords[u]
            coords_list.append([float(lng), float(lat)])
            if idx + 1 < len(node_seq):
                v = node_seq[idx + 1]
                total_m += self.edge_len_lookup.get((u, v), 0.0)

        return coords_list, round(total_m / 1000.0, 2)

    def _serialize_poi_base(self, row: pd.Series) -> dict:
        address = row["address"] if row["address"] else row["street"]
        cat = row["category"] if row["category"] else row["amenity"]
        return {
            "poi_id": int(row["poi_id"]),
            "name": row["name"],
            "amenity": cat,
            "category": cat,
            "sub_type": row["sub_type"] or cat,
            "street": row["street"],
            "address": address,
            "opening_hours": row["opening_hours"] or None,
            "cuisine": row["cuisine"] or None,
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
        }

    def solve(
        self,
        people: list[dict],
        alpha: float = 0.5,
        depart_hour: float | None = None,
        amenity_filter: str = "all",
        max_minutes: float = 35.0,
    ):
        t0 = time.perf_counter()
        k = len(people)
        sources = [int(self.tree.query([p["lat"], p["lng"]])[1]) for p in people]

        # Chạy C-level Dijkstra có giới hạn thời gian; tự động mở rộng nếu nhóm ở quá xa nhau (VD: Nhà Bè <-> Thủ Đức)
        T_sec, preds = self._run_multi_source_dijkstra(sources, depart_hour, limit_sec=max_minutes * 60.0)
        T_min = T_sec / 60.0
        F_sum = np.sum(T_min, axis=0)
        F_max = np.max(T_min, axis=0)
        cost_all = (1.0 - alpha) * (F_sum / k) + alpha * F_max

        if not np.isfinite(np.min(cost_all)):
            T_sec, preds = self._run_multi_source_dijkstra(sources, depart_hour, limit_sec=None)
            T_min = T_sec / 60.0
            F_sum = np.sum(T_min, axis=0)
            F_max = np.max(T_min, axis=0)
            cost_all = (1.0 - alpha) * (F_sum / k) + alpha * F_max

        best_node = int(np.argmin(cost_all))
        best_lat, best_lng = self.coords[best_node]
        zone_name = f"Khu vực {self.node_names[best_node]}"

        routes_geojson = []
        times_per_person = []
        for i, p in enumerate(people):
            path_coords, dist_km = self._reconstruct_path_and_km(preds[i], sources[i], best_node)
            path_coords.insert(0, [float(p["lng"]), float(p["lat"])])
            t_val = round(float(T_min[i, best_node]), 1)

            times_per_person.append({
                "name": p["name"],
                "minutes": t_val,
                "km": dist_km,
                "snapped_coord": [float(self.coords[sources[i], 1]), float(self.coords[sources[i], 0])],
            })
            routes_geojson.append({
                "type": "Feature",
                "properties": {"person_index": i, "name": p["name"], "minutes": t_val, "km": dist_km},
                "geometry": {"type": "LineString", "coordinates": path_coords},
            })

        # Lọc & xếp hạng Top 25 địa điểm theo nhóm danh mục
        poi_nodes = self.df_pois["node_idx"].values
        T_pois = T_min[:, poi_nodes]
        poi_f_sum = np.sum(T_pois, axis=0)
        poi_f_max = np.max(T_pois, axis=0)
        poi_cost = (1.0 - alpha) * (poi_f_sum / k) + alpha * poi_f_max

        df_res = self.df_pois.copy()
        df_res["f_sum"] = np.round(poi_f_sum, 1)
        df_res["f_max"] = np.round(poi_f_max, 1)
        df_res["score"] = np.round(poi_cost, 2)
        for i in range(k):
            df_res[f"p_{i}"] = np.round(T_pois[i], 1)

        df_res = df_res[np.isfinite(df_res["score"])]
        if amenity_filter != "all":
            df_res = df_res[df_res["category"] == amenity_filter]

        top_df = df_res.sort_values("score").head(25)
        top_pois = []
        for _, row in top_df.iterrows():
            item = self._serialize_poi_base(row)
            item.update({
                "f_sum": float(row["f_sum"]),
                "f_max": float(row["f_max"]),
                "score": float(row["score"]),
                "person_times": [{"name": people[i]["name"], "minutes": float(row[f"p_{i}"])} for i in range(k)],
            })
            top_pois.append(item)

        return {
            "compute_ms": round((time.perf_counter() - t0) * 1000, 2),
            "optimum": {
                "node_idx": best_node,
                "zone_name": zone_name,
                "lat": float(best_lat),
                "lng": float(best_lng),
                "f_sum": round(float(F_sum[best_node]), 1),
                "f_max": round(float(F_max[best_node]), 1),
            },
            "times_per_person": times_per_person,
            "routes": {"type": "FeatureCollection", "features": routes_geojson},
            "top_pois": top_pois,
        }

    def get_poi_routes(self, people: list[dict], poi_id: int, depart_hour: float | None = None):
        poi_row = self.df_pois[self.df_pois["poi_id"] == poi_id].iloc[0]
        target_node = int(poi_row["node_idx"])
        sources = [int(self.tree.query([p["lat"], p["lng"]])[1]) for p in people]

        T_sec, preds = self._run_multi_source_dijkstra(sources, depart_hour, limit_sec=None)

        routes_geojson = []
        person_times = []
        for i, p in enumerate(people):
            path_coords, dist_km = self._reconstruct_path_and_km(preds[i], sources[i], target_node)
            path_coords.insert(0, [float(p["lng"]), float(p["lat"])])
            path_coords.append([float(poi_row["lng"]), float(poi_row["lat"])])
            t_val = round(float(T_sec[i, target_node] / 60.0), 1)

            person_times.append({"name": p["name"], "minutes": t_val, "km": dist_km})
            routes_geojson.append({
                "type": "Feature",
                "properties": {"person_index": i, "name": p["name"], "minutes": t_val, "km": dist_km},
                "geometry": {"type": "LineString", "coordinates": path_coords},
            })

        item = self._serialize_poi_base(poi_row)
        item["person_times"] = person_times
        item["f_sum"] = round(sum(x["minutes"] for x in person_times), 1)
        item["f_max"] = round(max(x["minutes"] for x in person_times), 1)

        return {
            "poi": item,
            "routes": {"type": "FeatureCollection", "features": routes_geojson},
        }

    def get_custom_routes(
        self,
        people: list[dict],
        name: str,
        address: str,
        lat: float,
        lng: float,
        depart_hour: float | None = None,
    ):
        target_node = int(self.tree.query([lat, lng])[1])
        sources = [int(self.tree.query([p["lat"], p["lng"]])[1]) for p in people]
        T_sec, preds = self._run_multi_source_dijkstra(sources, depart_hour, limit_sec=None)

        routes_geojson = []
        person_times = []
        for i, p in enumerate(people):
            path_coords, dist_km = self._reconstruct_path_and_km(preds[i], sources[i], target_node)
            path_coords.insert(0, [float(p["lng"]), float(p["lat"])])
            path_coords.append([float(lng), float(lat)])
            t_val = round(float(T_sec[i, target_node] / 60.0), 1)

            person_times.append({"name": p["name"], "minutes": t_val, "km": dist_km})
            routes_geojson.append({
                "type": "Feature",
                "properties": {"person_index": i, "name": p["name"], "minutes": t_val, "km": dist_km},
                "geometry": {"type": "LineString", "coordinates": path_coords},
            })

        resolved_addr = address or f"Gần {self.node_names[target_node]}"
        custom_poi = {
            "poi_id": -1,
            "name": name,
            "amenity": "custom",
            "category": "custom",
            "sub_type": "custom",
            "street": str(self.node_names[target_node]),
            "address": resolved_addr,
            "opening_hours": None,
            "cuisine": None,
            "lat": float(lat),
            "lng": float(lng),
            "person_times": person_times,
            "f_sum": round(sum(x["minutes"] for x in person_times), 1),
            "f_max": round(max(x["minutes"] for x in person_times), 1),
        }

        return {
            "poi": custom_poi,
            "routes": {"type": "FeatureCollection", "features": routes_geojson},
        }