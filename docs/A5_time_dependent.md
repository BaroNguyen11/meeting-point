# A5: Mô hình Định tuyến Phụ thuộc Thời gian (Time-Dependent Routing)

## 1. Mục tiêu
Mô phỏng tác động của ùn tắc giao thông theo khung giờ đến thời gian di chuyển và vị trí điểm hẹn tối ưu, so sánh trực tiếp giữa giờ thấp điểm (`10:00`) và giờ cao điểm chiều (`17:30`).

## 2. Phương pháp
- **Hàm trọng số động $w(e, t)$ tuân thủ tính chất FIFO:** Phân tách mạng lưới thành đường trục chính và đường nhánh/hẻm dựa trên vận tốc lưu thông cơ sở. Vào khung giờ cao điểm (`16:30 – 19:00`), áp dụng hệ số nhân thời gian $\times 1.85$ cho trục chính và $\times 1.25$ cho đường nhánh/hẻm.
- **Thuật toán Time-Dependent Dijkstra:** Cập nhật đồng hồ thời gian thực tại mỗi nút trung gian để tính chi phí động cho từng cạnh kế tiếp.

## 3. Kết quả thực nghiệm ($k = 4$ người)
| Khung giờ | Tiêu chí | Đỉnh tối ưu | Thời gian từng người (phút) | Tổng $F_{\text{sum}}$ | Lâu nhất $F_{\text{max}}$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **10:00 (Thấp điểm)** | Sum | `#1828` | `[7.9, 0.1, 10.1, 10.1]` | `28.2p` | `10.1p` |
| **10:00 (Thấp điểm)** | Minimax | `#1813` | `[8.7, 3.5, 8.7, 8.8]` | `29.7p` | `8.8p` |
| **17:30 (Cao điểm)** | Sum | `#1828` | `[10.9, 0.1, 15.2, 14.0]` | `40.3p` | `15.2p` |
| **17:30 (Cao điểm)** | Minimax | `#1671` | `[11.5, 3.8, 13.0, 12.9]` | `41.2p` | `13.0p` |

## 4. Phân tích & Kết luận
- **Độ trơ của hàm Sum:** Điểm tối ưu `Sum` giữ nguyên tại `#1828` bất kể giờ cao điểm, tổng thời gian nhóm tăng $+12.1\text{p}$ ($+42.9\%$).
- **Độ nhạy của hàm Minimax:** Điểm tối ưu dịch chuyển **`329.2 mét`** về phía Đông (từ `#1813` sang `#1671`) nhằm bù trừ mức độ ùn tắc trên hướng di chuyển từ Hàng Xanh, giữ chênh lệch giữa người đi xa nhất và người thứ hai chỉ ở mức $0.1\text{p}$ (`13.0p` vs `12.9p`).