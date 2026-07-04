from pydantic import BaseModel, Field


class Zone(BaseModel):
    name: str
    x: int
    y: int
    zone_type: str
    color: str | None
    max_drones: int


class Connection(BaseModel):
    from_zone: Zone
    to_zone: Zone
    max_capacity: int


class Map(BaseModel):
    drone_nb: int = Field(ge=1)
    zones: dict[str, Zone]
    connection: list[Connection]
    start_name: str
    end_name: str
