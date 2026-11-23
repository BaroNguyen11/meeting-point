# A1: Xây dựng Đồ thị Giao thông Đường bộ TP.HCM cho Xe máy

## 1. Mục tiêu
Chuyển đổi dữ liệu bản đồ mở OpenStreetMap (OSM) thành cấu trúc đồ thị có hướng, có trọng số thời gian di chuyển (`travel_time`) phản ánh đặc thù giao thông xe máy tại TP.HCM, lưu trữ dưới dạng ma trận kề thưa (CSR) để phục vụ truy vấn thời gian thực trong RAM.

## 2. Phương pháp & Mô hình hóa chi phí
- **Nguồn dữ liệu:** OpenStreetMap qua thư viện `OSMnx` (`network_type="all"`, `simplify=True`).
- **Tập cạnh xe máy:** Giữ lại toàn bộ mạng lưới đường và hẻm nội bộ; loại bỏ cao tốc và đường dành riêng cho người đi bộ (`motorway`, `footway`, `steps`, `cycleway`, `pedestrian`, `path`, `track`).
- **Làm sạch liên thông:** Trích xuất thành phần liên thông mạnh lớn nhất (Largest Strongly Connected Component) nhằm đảm bảo mọi cặp đỉnh $(u, v)$ đều tồn tại đường đi hợp lệ theo luật đường một chiều.
- **Hàm chi phí cạnh $w(u, v)$ (đơn vị: giây):**
  $$w(u, v) = \frac{\text{length}(u, v)}{v_{\text{moto}}(\text{highway})} + \text{penalty}(v)$$
  - Vận tốc $v_{\text{moto}}$ phân tầng theo loại đường: `trunk` (35 km/h), `primary` (32 km/h), `secondary` (30 km/h), `tertiary` (28 km/h), `residential` (22 km/h), `living_street/service` (15 km/h).
  - Phạt nút giao $\text{penalty}(v)$ dựa trên bậc đường giao nhau (`street_count`): $+8\text{s}$ tại ngã tư lớn ($\ge 4$ nhánh), $+3\text{s}$ tại ngã ba ($3$ nhánh), $0\text{s}$ tại điểm nối tiếp.

## 3. Kết quả thực nghiệm (Khu vực Trung tâm: Q1, Q3, Bình Thạnh)
- **Quy mô đồ thị sau làm sạch:** $14,104$ đỉnh (ngã rẽ) và $31,782$ cạnh có hướng.
- **Hiệu năng tiền xử lý:** Tải và làm sạch OSM mất $118.3\text{s}$; tính trọng số và nén ma trận thưa `scipy.sparse.csr_matrix` mất $0.5\text{s}$.
- **Định dạng lưu trữ:** `hcm_center_moto_adj.npz` (ma trận kề trọng số `float32`) và `hcm_center_moto_meta.npz` (tọa độ GPS và OSM Node ID).

## 4. Hạn chế hiện tại
- Vận tốc theo loại đường đang sử dụng giá trị cố định (static), chưa phản ánh biến động kẹt xe theo khung giờ cao điểm (sẽ xử lý ở A5).
- Chưa phân biệt phạt rẽ trái cắt dòng so với đi thẳng hoặc rẽ phải.