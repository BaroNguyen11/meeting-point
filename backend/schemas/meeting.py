from pydantic import BaseModel, Field


class PersonInput(BaseModel):
    id: str | None = None
    name: str
    address: str | None = None
    lat: float
    lng: float


class SolveRequest(BaseModel):
    people: list[PersonInput] = Field(..., min_length=2, max_length=8)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    depart_hour: float | None = Field(None, ge=0.0, lt=24.0)
    amenity_filter: str = "all"
    max_minutes: float = Field(35.0, ge=5.0, le=90.0)


class PoiRouteRequest(BaseModel):
    people: list[PersonInput] = Field(..., min_length=2, max_length=8)
    poi_id: int
    depart_hour: float | None = None


class CustomRouteRequest(BaseModel):
    people: list[PersonInput] = Field(..., min_length=2, max_length=8)
    name: str
    address: str | None = None
    lat: float
    lng: float
    depart_hour: float | None = None


class RoomCreateRequest(BaseModel):
    people: list[PersonInput] = Field(..., min_length=2, max_length=8)
    alpha: float = 0.5
    is_rush_hour: bool = False
    amenity_filter: str = "all"
    max_minutes: float = 35.0
    selected_poi_id: int | None = None