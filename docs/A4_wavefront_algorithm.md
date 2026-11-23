# A4: Thuật toán Nước Loang Đồng Bộ (Synchronized Multi-Source Wavefront)

## 1. Mục tiêu
Thay thế phương pháp chạy $k$ lần Dijkstra độc lập (quét toàn bộ $k \times |V|$ trạng thái) bằng một hàng đợi ưu tiên đồng bộ theo thời gian thực tế $t$, cho phép dừng sớm (Early Termination) mà vẫn đảm bảo tính chính xác tuyệt đối (Exactness) cho cả bài toán Minimax và Sum.

## 2. Cơ sở toán học & Điều kiện dừng chính xác
Gọi $t$ là thời điểm của trạng thái nhỏ nhất vừa lấy ra từ hàng đợi ưu tiên chung `pq`. Do tính chất đơn điệu của trọng số dương ($w(u,v) > 0$), mọi đỉnh $v$ chưa được người $i$ chạm tới chắc chắn thỏa mãn $T_i[v] \ge t$.

1. **Bài toán Minimax ($\min_v \max_i T_i[v]$):**
   - Đỉnh $v^*$ đầu tiên được cả $k$ vùng loang chạm tới có giá trị $\max_i T_i[v^*] = t$. Mọi đỉnh chưa đủ $k$ người chạm tới đều có ít nhất một thành phần $\ge t$, do đó $v^*$ là nghiệm tối ưu toàn cục và thuật toán dừng ngay lập tức.
2. **Bài toán Sum ($\min_v \sum_i T_i[v]$ — Branch & Bound):**
   - *Phát hiện điểm mù của cận dưới ngây thơ:* Điều kiện dừng $k \cdot t \ge \text{best\_sum}$ gây dừng sớm sai lệch (cho nghiệm `#1813` với `29.66p` thay vì `#1828` với `28.16p`), vì bỏ qua các đỉnh bất đối xứng đã có $c \in [1, k-1]$ người chạm tới từ sớm.
   - *Cận dưới toàn cục chính xác (Exact Global Lower Bound):* Duy trì tập đỉnh dang dở $\mathcal{A}$ ($1 \le \text{count}[v] < k$), cận dưới chặt tại thời điểm $t$ là:
     $$\text{LB}(t) = \min\left(k \cdot t, \ \min_{v \in \mathcal{A}} \left[\text{partial\_sum}[v] + (k - \text{count}[v]) \cdot t\right]\right)$$
   - Thuật toán dừng an toàn khi $\text{LB}(t) \ge \text{best\_sum}$.

## 3. Kết quả thực nghiệm ($|V| = 14,104$, $k = 4$, tổng không gian $56,416$ trạng thái)
| Thuật toán | Đỉnh tối ưu | Giá trị mục tiêu | Số trạng thái mở rộng | Tỷ lệ không gian đã quét |
| :--- | :--- | :--- | :--- | :--- |
| Full Dijkstra (Baseline) | `#1813` / `#1828` | `8.76p` / `28.16p` | `56,416` | `100.0%` |
| **Wavefront Minimax** | **`#1813`** | **`8.76p` (Exact)** | **`15,790`** | **`28.0%` (Giảm 72.0%)** |
| **Wavefront Sum (Exact)** | **`#1828`** | **`28.16p` (Exact)** | **`24,662`** | **`43.7%` (Giảm 56.3%)** |