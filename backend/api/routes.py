from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.core.config import settings
from backend.db.sqlite_cache import storage
from backend.schemas.meeting import (
    CustomRouteRequest,
    PoiRouteRequest,
    RoomCreateRequest,
    SolveRequest,
)
from backend.services.geocoding_service import (
    forward_geocode,
    reverse_geocode,
    search_places_in_area,
)
from backend.services.graph_engine import GraphEngine
from backend.services.review_service import (
    attach_manual_tiktok_to_poi,
    fetch_real_poi_enrichment,
)

router = APIRouter(prefix="/api")

engine = GraphEngine(
    adj_path=settings.GRAPH_ADJ_PATH,
    meta_path=settings.GRAPH_META_PATH,
    poi_path=settings.POI_CSV_PATH,
)


class AttachTikTokRequest(BaseModel):
    poi_name: str
    street: str = ""
    tiktok_url: str


@router.get("/health")
def health_check():
    return {"status": "ok", "nodes": engine.num_nodes, "pois": len(engine.df_pois)}


@router.get("/geocode")
async def api_geocode(
    q: str = Query(..., min_length=2),
    lat: float = Query(10.7769),
    lng: float = Query(106.7009),
):
    return {"results": await forward_geocode(q, engine, focus_lat=lat, focus_lng=lng)}


@router.get("/search-area")
def api_search_area(
    q: str = Query(..., min_length=1),
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
):
    return {"places": search_places_in_area(engine, q, west, south, east, north)}


@router.get("/reverse-geocode")
async def api_reverse_geocode(lat: float, lng: float):
    return {"address": await reverse_geocode(lat, lng, engine)}


@router.post("/solve")
def api_solve(req: SolveRequest):
    return engine.solve(
        people=[p.model_dump() for p in req.people],
        alpha=req.alpha,
        depart_hour=req.depart_hour,
        amenity_filter=req.amenity_filter,
        max_minutes=req.max_minutes,
    )


@router.post("/poi-routes")
def api_poi_routes(req: PoiRouteRequest):
    if req.poi_id not in engine.df_pois["poi_id"].values:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return engine.get_poi_routes(
        people=[p.model_dump() for p in req.people],
        poi_id=req.poi_id,
        depart_hour=req.depart_hour,
    )


@router.post("/custom-route")
def api_custom_route(req: CustomRouteRequest):
    return engine.get_custom_routes(
        people=[p.model_dump() for p in req.people],
        name=req.name,
        address=req.address or "",
        lat=req.lat,
        lng=req.lng,
        depart_hour=req.depart_hour,
    )


@router.get("/pois/{poi_id}/reviews")
async def api_poi_reviews(poi_id: int):
    matches = engine.df_pois[engine.df_pois["poi_id"] == poi_id]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    row = matches.iloc[0]
    return await fetch_real_poi_enrichment(
        poi_name=row["name"],
        street=row["street"] or row["address"],
        lat=float(row["lat"]),
        lng=float(row["lng"]),
    )


@router.get("/custom-reviews")
async def api_custom_reviews(name: str, address: str = "", lat: float = 10.78, lng: float = 106.70):
    return await fetch_real_poi_enrichment(
        poi_name=name,
        street=address,
        lat=lat,
        lng=lng,
    )


@router.post("/attach-tiktok")
async def api_attach_tiktok(req: AttachTikTokRequest):
    updated = await attach_manual_tiktok_to_poi(req.poi_name, req.street, req.tiktok_url)
    if not updated:
        raise HTTPException(status_code=400, detail="Link TikTok không hợp lệ hoặc không truy xuất được video")
    return updated


@router.post("/rooms")
def api_create_room(req: RoomCreateRequest):
    room_id = storage.create_room(req.model_dump())
    return {"room_id": room_id}


@router.get("/rooms/{room_id}")
def api_get_room(room_id: str):
    payload = storage.get_room(room_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Phòng chia sẻ không tồn tại")
    return payload

@router.get("/search-area")
async def api_search_area(
    q: str = Query(..., min_length=1),
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
):
    return {"places": await search_places_in_area(engine, q, west, south, east, north)}