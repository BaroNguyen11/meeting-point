# A2: Tính Trường Thời Gian $T_i(x)$ & Đánh giá Hiệu năng Dijkstra

## 1. Mục tiêu
Xây dựng module truy vấn đường đi ngắn nhất từ $k$ vị trí xuất phát tới toàn bộ tập đỉnh $V$ trên đồ thị đường bộ thật, đảm bảo tốc độ phản hồi thời gian thực (< 50 ms) để phục vụ tính năng tương tác kéo-thả vị trí trên giao diện.

## 2. Phương pháp
- **Spatial Indexing (Map-matching cơ bản):** Sử dụng cấu trúc cây `scipy.spatial.cKDTree` trên mảng tọa độ $(lat, lng)$ để ánh xạ tọa độ GPS của người dùng về đỉnh gần nhất trên đồ thị.
- **Tính trường thời gian One-to-All:** So sánh 2 phương pháp cài đặt thuật toán Dijkstra trên đồ thị có hướng ($|V| = 14,104$, $|E| = 31,782$) với $k = 4$ người xuất phát tại các điểm thực tế (Chợ Bến Thành, Hồ Con Rùa, Hàng Xanh, Vạn Kiếp):
  1. **Python thuần (`heapq` + Adjacency Dict):** Cài đặt thủ công hàng đợi ưu tiên nhị phân để làm nền tảng phát triển thuật toán nước loang ở A4.
  2. **SciPy C-engine (`scipy.sparse.csgraph.dijkstra`):** Thực thi trực tiếp trên ma trận thưa CSR bằng mã biên dịch C/Cython.

## 3. Kết quả thực nghiệm
| Chỉ số đo lường | Kết quả đo được | Ghi chú |
| :--- | :--- | :--- |
| Thời gian nạp đồ thị từ ổ cứng lên RAM | `30.74 ms` | Đọc từ file nén `.npz` |
| Thời gian chạy Python thuần (`heapq`) | `88.18 ms` | Cho cả $k=4$ nguồn |
| Thời gian chạy SciPy C-engine | `7.53 ms` | Nhanh hơn **11.7 lần** |
| Sai số tuyệt đối lớn nhất ($\max |T_{\text{scipy}} - T_{\text{py}}|$) | `0.000000 s` | Khớp chính xác tuyệt đối |

## 4. Nhận xét & Lựa chọn kiến trúc
- Với quy mô trung tâm TP.HCM ($14,104$ đỉnh), `scipy.sparse.csgraph.dijkstra` chỉ mất `7.53 ms`, đủ sức đáp ứng truy vấn trực tiếp trong RAM mà không cần chia lưới xấp xỉ.
- Bản cài đặt `heapq` đạt `88.18 ms` vẫn đủ nhanh để làm lõi cho thuật toán duyệt đồng bộ nhiều nguồn có cắt tỉa (A4).