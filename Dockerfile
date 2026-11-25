FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data/hcm_metro_pois.csv ./data/hcm_metro_pois.csv
COPY data/dataset_manifest.json ./data/dataset_manifest.json

RUN mkdir -p data && \
    curl -fL "https://github.com/BaroNguyen11/meeting-point/releases/download/v1.0.0/hcm_metro_moto_adj.npz" -o data/hcm_metro_moto_adj.npz && \
    curl -fL "https://github.com/BaroNguyen11/meeting-point/releases/download/v1.0.0/hcm_metro_moto_meta.npz" -o data/hcm_metro_moto_meta.npz

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]