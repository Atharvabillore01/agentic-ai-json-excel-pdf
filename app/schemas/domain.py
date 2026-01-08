from pydantic import BaseModel
from typing import Optional, Dict, List

class Park(BaseModel):
    park_id: Optional[str]
    park_name: str
    district: str
    sector: Optional[str]
    status: Optional[str]
    total_land: float
    metadata: Dict

class Plot(BaseModel):
    plot_id: Optional[str]
    plot_number: str
    park_name: str
    size_sq_m: float
    rate: float
    status: Optional[str]
    metadata: Dict

class POI(BaseModel):
    poi_id: Optional[str]
    name: str
    type: str
    code: Optional[str]
    state: Optional[str]
    district: Optional[str]
    address: Optional[str]
    location: Dict
    metadata: Dict

class PolicyChunk(BaseModel):
    chunk_id: str
    text: str
    page: int
    source: str
