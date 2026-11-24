import os
from pathlib import Path


def _load_dotenv(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


class Settings:
    GRAPH_ADJ_PATH: str = os.getenv("GRAPH_ADJ_PATH", "data/hcm_metro_moto_adj.npz")
    GRAPH_META_PATH: str = os.getenv("GRAPH_META_PATH", "data/hcm_metro_moto_meta.npz")
    POI_CSV_PATH: str = os.getenv("POI_CSV_PATH", "data/hcm_metro_pois.csv")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/meetpoint.db")

    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")


settings = Settings()