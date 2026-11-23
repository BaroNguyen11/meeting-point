import time
import numpy as np
import osmnx as ox
from scipy.sparse import csr_matrix, save_npz

# Cấu hình vận tốc xe máy tại TP.HCM (km/h)
MOTO_SPEED_KMH = {
    "trunk": 35.0, "trunk_link": 25.0,
    "primary": 32.0, "primary_link": 22.0,
    "secondary": 30.0, "secondary_link": 20.0,
    "tertiary": 28.0, "tertiary_link": 20.0,
    "residential": 22.0, "unclassified": 22.0,
    "living_street": 15.0, "service": 15.0,
}
DEFAULT_SPEED_KMH = 20.0

# Các loại đường cấm xe máy hoặc chỉ dành cho người đi bộ
EXCLUDED_HIGHWAYS = {"motorway", "motorway_link", "footway", "steps", "cycleway", "pedestrian", "path", "track"}

def build_moto_graph(place_name, output_prefix):
    t0 = time.time()
    print(f"[1/4] Đang tải dữ liệu OSM cho: {place_name}...")
    # Dùng network_type="all" để lấy cả hẻm nhỏ cho xe máy, sau đó tự lọc đường cấm
    G_raw = ox.graph_from_place(place_name, network_type="all", simplify=True)
    
    # Lọc bỏ đường cao tốc và đường đi bộ
    edges_to_remove = []
    for u, v, k, data in G_raw.edges(keys=True, data=True):
        hw = data.get("highway", "")
        hw_set = set(hw) if isinstance(hw, list) else {hw}
        if hw_set & EXCLUDED_HIGHWAYS:
            edges_to_remove.append((u, v, k))
    G_raw.remove_edges_from(edges_to_remove)
    
    # Giữ lại thành phần liên thông mạnh lớn nhất
    G = ox.truncate.largest_component(G_raw, strongly=True)
    num_nodes = G.number_of_nodes()
    print(f"[2/4] Đồ thị sau làm sạch: {num_nodes:,} nút, {G.number_of_edges():,} cạnh ({time.time() - t0:.1f}s)")
    
    # Ánh xạ OSM ID <-> Chỉ số ma trận 0..N-1
    node_list = list(G.nodes())
    node_to_idx = {osm_id: idx for idx, osm_id in enumerate(node_list)}
    
    # Lưu tọa độ (lat, lng) và OSM ID của từng đỉnh
    coords = np.zeros((num_nodes, 2), dtype=np.float64)
    for idx, osm_id in enumerate(node_list):
        coords[idx, 0] = G.nodes[osm_id]["y"]  # Latitude
        coords[idx, 1] = G.nodes[osm_id]["x"]  # Longitude
        
    print("[3/4] Đang tính chi phí xe máy và nén ma trận thưa CSR...")
    # Dùng dict để gộp các cạnh song song (u -> v), giữ cạnh có travel_time nhỏ nhất
    best_edges = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        hw = data.get("highway", "")
        if isinstance(hw, list):
            hw = hw[0]
            
        speed_ms = MOTO_SPEED_KMH.get(hw, DEFAULT_SPEED_KMH) * 1000 / 3600
        run_time = data.get("length", 0.0) / speed_ms
        
        street_count = G.nodes[v].get("street_count", 2)
        penalty = 8.0 if street_count >= 4 else (3.0 if street_count == 3 else 0.0)
        travel_time = max(0.1, round(run_time + penalty, 2))  # Đảm bảo trọng số > 0
        
        u_idx, v_idx = node_to_idx[u], node_to_idx[v]
        if (u_idx, v_idx) not in best_edges or travel_time < best_edges[(u_idx, v_idx)]:
            best_edges[(u_idx, v_idx)] = travel_time
            
    # Tạo các mảng row, col, data để xây csr_matrix
    rows = np.array([pair[0] for pair in best_edges.keys()], dtype=np.int32)
    cols = np.array([pair[1] for pair in best_edges.keys()], dtype=np.int32)
    weights = np.array(list(best_edges.values()), dtype=np.float32)
    
    adj_matrix = csr_matrix((weights, (rows, cols)), shape=(num_nodes, num_nodes))
    
    # Xuất ra file nén .npz
    save_npz(f"{output_prefix}_adj.npz", adj_matrix)
    np.savez_compressed(
        f"{output_prefix}_meta.npz",
        coords=coords,
        node_ids=np.array(node_list, dtype=np.int64)
    )
    print(f"[4/4] Hoàn tất! Đã lưu tại {output_prefix}_adj.npz và {output_prefix}_meta.npz (Tổng: {time.time() - t0:.1f}s)")

if __name__ == "__main__":
    # Test trước với khu vực trung tâm (Quận 1 + Quận 3 + Bình Thạnh) để đủ rộng và chạy nhanh (~15-30s)
    # Khi nào muốn build toàn TP.HCM, chỉ cần đổi thành "Ho Chi Minh City, Vietnam"
    places = [
        "District 1, Ho Chi Minh City, Vietnam",
        "District 3, Ho Chi Minh City, Vietnam",
        "Binh Thanh District, Ho Chi Minh City, Vietnam"
    ]
    build_moto_graph(places, "data/hcm_center_moto")