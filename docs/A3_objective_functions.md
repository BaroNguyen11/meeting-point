# A3: Phân tích Họ Hàm Mục Tiêu $F(x)$ & Đường biên Pareto

## 1. Mục tiêu
Đánh giá sự khác biệt về vị trí địa lý và phân bổ thời gian di chuyển giữa các hàm mục tiêu định vị trên đồ thị thật (Q1 – Q3 – Bình Thạnh, $|V|=14,104$), đồng thời trích xuất tập lời giải tối ưu Pareto phục vụ tương tác người dùng.

## 2. Kết quả thực nghiệm ($k = 4$ người)
| Hàm mục tiêu $F(x)$ | Đỉnh tối ưu | Thời gian từng người (phút) | Tổng $F_{\text{sum}}$ | Lâu nhất $F_{\text{max}}$ |
| :--- | :--- | :--- | :--- | :--- |
| **Sum ($\sum T_i$)** | `#1828` | `[7.9, 0.1, 10.1, 10.1]` | `28.2p` | `10.1p` |
| **Minimax ($\max T_i$)** | `#1813` | `[8.7, 3.5, 8.7, 8.8]` | `29.7p` | `8.8p` |
| **Sum of Squares ($\sum T_i^2$)** | `#11378` | `[11.4, 4.9, 5.7, 6.7]` | `28.7p` | `11.4p` |
| **Mean + $2\cdot\text{Std}$** | `#11378` | `[11.4, 4.9, 5.7, 6.7]` | `28.7p` | `11.4p` |
| **Weighted (Ưu tiên Phi $\times 2$)** | `#2935` | `[12.5, 6.0, 5.9, 5.0]` | `29.4p` | `12.5p` |

## 3. Phân tích & Phát hiện chính
- **Hiện tượng điểm dính (Median Property):** Hàm `Sum` hội tụ sát vị trí của Bình (`0.1p`) tại khu vực Hồ Con Rùa, tối ưu tổng thời gian (`28.2p`) nhưng bắt hai thành viên ở Bình Thạnh di chuyển trên `10p`.
- **Sự đánh đổi (Trade-off):** Hàm `Minimax` dịch chuyển điểm hẹn về phía ranh giới Q1 – Bình Thạnh (`#1813`), chấp nhận tăng tổng thời gian cả nhóm thêm `+1.5p` (`29.7p`) để cân bằng thời gian ba hướng (`8.7p – 8.8p`).
- **Tập Pareto Front:** Giảm không gian tìm kiếm từ $14,104$ đỉnh xuống còn đúng **$7$ đỉnh tối ưu không bị trội**, tạo cơ sở trực tiếp cho thanh trượt điều chỉnh mức độ công bằng trên giao diện.