# A6: Nội suy Trường Thời Gian & Tạo Dải Màu Isochrone (Contour Map)

## 1. Mục tiêu
Chuyển đổi các giá trị thời gian rời rạc trên $14,104$ đỉnh đồ thị thành bề mặt liên tục 2D và các dải đồng mức thời gian (Isochrone contours), phục vụ trực quan hóa vùng tiếp cận và lớp phủ heatmap trên bản đồ web.

## 2. Phương pháp xử lý không gian
1. **Rời rạc hóa lưới đều (Grid Rasterization):** Phủ lưới $200 \times 200$ điểm bao quanh khung tọa độ Q1 – Q3 – Bình Thạnh.
2. **Nội suy lân cận & Khử răng cưa:** Ánh xạ giá trị từ đỉnh đường gần nhất qua `cKDTree`, kết hợp bộ lọc làm mượt chuẩn hóa (Normalized Gaussian Filter, $\sigma = 1.2$) để tạo ranh giới đồng mức mượt mà.
3. **Chặn tràn qua mặt nước (Water/Empty Masking):** Áp ngưỡng khoảng cách tối đa tới mạng lưới đường bộ $d_{\text{road}} \le 180\text{m}$. Các ô lưới vượt ngưỡng (thuộc lòng sông Sài Gòn, kênh Nhiêu Lộc hoặc khu vực không có đường giao thông) được gán `NaN` nhằm loại bỏ hoàn toàn hiện tượng loang màu xuyên sông.

## 3. Kết quả thực nghiệm
- **Thời gian sinh lưới & nội suy:** `< 15 ms` trên lưới $40,000$ điểm.
- **Chất lượng hình học:** Biên giới Sông Sài Gòn, kênh rạch và bán đảo Thanh Đa được bảo toàn sắc nét; hình dạng các dải isochrone phản ánh đúng tốc độ lưu thông thực tế theo hướng trục đường thay vì hình tròn đồng tâm như đường chim bay.