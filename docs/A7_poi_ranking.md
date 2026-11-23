# A7: Khai thác Tập POI Thật & Xếp hạng Đa tiêu chí

## 1. Mục tiêu
Chuyển đổi bài toán từ tìm đỉnh giao thông trừu tượng (Continuous) sang đề xuất danh sách địa điểm gặp mặt thực tế (Discrete POIs: quán cà phê, nhà hàng), kết hợp lọc ràng buộc và hàm điểm cân bằng đa mục tiêu.

## 2. Phương pháp
- **Thu thập & Chuẩn hóa POI:** Trích xuất $1,392$ địa điểm ăn uống/cà phê từ OpenStreetMap (`amenity` $\in$ `{cafe, restaurant, fast_food}`) tại Q1, Q3, Bình Thạnh. Các đối tượng dạng đa giác (Polygon) được chiếu về hệ tọa độ mét `EPSG:32648` (UTM Zone 48N) để lấy tâm hình học chính xác trước khi ánh xạ về đỉnh đồ thị gần nhất qua `cKDTree` (ngưỡng khoảng cách tối đa $150\text{m}$).
- **Lọc cứng & Xếp hạng tuyến tính hóa Pareto:**
  $$\text{Cost}_{\alpha}(p) = (1 - \alpha) \cdot \frac{F_{\text{sum}}(p)}{k} + \alpha \cdot F_{\text{max}}(p), \quad \alpha \in [0, 1]$$

## 3. Kết quả thực nghiệm ($\alpha = 0.5$, ngưỡng $F_{\text{max}} \le 15\text{p}$)
| Hạng | Tên địa điểm | An | Bình | Chi | Phi | Tổng $F_{\text{sum}}$ | Lâu nhất $F_{\text{max}}$ | Điểm chi phí |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Cafe Thứ 7** | `8.7p` | `3.5p` | `8.7p` | `8.8p` | `29.7p` | `8.8p` | `8.1125` |
| 2 | **Highlands Coffee** | `8.6p` | `3.3p` | `8.9p` | `8.9p` | `29.7p` | `8.9p` | `8.1625` |
| 4 | **The Coffee House** | `8.4p` | `0.6p` | `9.6p` | `9.7p` | `28.3p` | `9.7p` | `8.3875` |
| 5 | **Phuc Long** | `8.0p` | `2.8p` | `9.1p` | `9.5p` | `29.5p` | `9.5p` | `8.4375` |

## 4. Phát hiện chất lượng dữ liệu (Data Quality Findings)
- **Trùng lặp đa hình học (Node vs Polygon):** Một số thương hiệu (như `Phuc Long`) tồn tại đồng thời dưới dạng điểm và đa giác tòa nhà trên OSM; cần bổ sung bước khử trùng lặp theo khóa `(name, node_idx)`.
- **Nhiễu nhãn phân loại:** Xuất hiện quán ăn (`Miến Phở Gà`) được gắn thẻ `cafe` trên OSM, gợi ý cần kết hợp lọc từ khóa tên quán hoặc đối chiếu thêm nguồn dữ liệu phụ trợ ở giai đoạn sản phẩm.