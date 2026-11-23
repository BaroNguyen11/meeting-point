from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.engine import MeetingPointEngine

app = FastAPI(title="Meeting Point Finder Engine API", version="1.0.0")

# Cho phép Frontend (Next.js ở cổng 3000) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Engine 1 lần duy nhất trong RAM khi bật server
engine = MeetingPointEngine(
    adj_path="data/hcm_center_moto_adj.npz",
    meta_path="data/hcm_center_moto_meta.npz",
    poi_path="data/hcm_center_pois.csv",
)


class PersonInput(BaseModel):
    name: str
    lat: float
    lng: float


class SolveRequest(BaseModel):
    people: list[PersonInput] = Field(..., min_length=2, max_length=8)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    depart_hour: float | None = Field(None, ge=0.0, lt=24.0)
    amenity_filter: str = "all"


@app.get("/api/health")
def health_check():
    return {"status": "ok", "nodes": engine.num_nodes, "pois": len(engine.df_pois)}


@app.post("/api/solve")
def solve_meeting_point(req: SolveRequest):
    people_dicts = [p.model_dump() for p in req.people]
    return engine.solve(
        people=people_dicts,
        alpha=req.alpha,
        depart_hour=req.depart_hour,
        amenity_filter=req.amenity_filter,
    )


@app.post("/api/wavefront")
def get_wavefront_animation(req: SolveRequest):
    people_dicts = [p.model_dump() for p in req.people]
    return engine.compute_wavefront_edges(people=people_dicts, max_minutes=20.0)