FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY scripts ./scripts
COPY data/hcm_metro_pois.csv ./data/hcm_metro_pois.csv
COPY data/dataset_manifest.json ./data/dataset_manifest.json

# Tự động tải & build đồ thị 5x5 khi tạo image (hoặc bỏ dòng này nếu bạn mount volume / tải từ Release)
RUN python scripts/build_graph.py

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]