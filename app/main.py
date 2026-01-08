from fastapi import FastAPI
import time
import json
from datetime import datetime
from fastapi import Query
from app.core.cache import cache
from app.services.loader import load_all
from app.services.poi_distance import find_nearby_pois
from app.vectorstore.policy_index import build_all_indexes, search_policy
from app.utils.json_safe import json_safe
import logging
from app.middleware.timing import timing_middleware
from app.api.ask import router as ask_router
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)


app = FastAPI(title="MP Industrial Agent Backend")
app.include_router(ask_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.middleware("http")(timing_middleware)

@app.on_event("startup")
def startup():
    load_all()
    build_all_indexes()
    cache["last_updated"] = datetime.utcnow().isoformat()

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "states": list(cache["states"].keys()),
        "lastUpdated": cache["last_updated"]
    }

@app.get("/api/{state}/parks")
def parks(
    state: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    t0 = time.perf_counter()

    all_parks = cache["states"].get(state, {}).get("parks", [])
    total = len(all_parks)

    t1 = time.perf_counter()

    sliced = all_parks[offset : offset + limit]
    safe_parks = json_safe(sliced)

    t2 = time.perf_counter()

    payload_size_kb = len(
        json.dumps(safe_parks, default=str).encode("utf-8")
    ) / 1024

    print(
        f"[DEBUG][parks] state={state} "
        f"total={total} returned={len(safe_parks)} "
        f"limit={limit} offset={offset} | "
        f"fetch={(t1 - t0)*1000:.2f} ms | "
        f"slice+sanitize={(t2 - t1)*1000:.2f} ms | "
        f"payload={payload_size_kb:.1f} KB"
    )

    return {
        "meta": {
            "total": total,
            "returned": len(safe_parks),
            "limit": limit,
            "offset": offset
        },
        "data": safe_parks
    }

import time
import json
from app.utils.json_safe import json_safe

@app.get("/api/{state}/plots")
def plots(
    state: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    t0 = time.perf_counter()

    all_plots = cache["states"].get(state, {}).get("plots", [])
    total = len(all_plots)

    t1 = time.perf_counter()

    sliced = all_plots[offset : offset + limit]
    safe_plots = json_safe(sliced)

    t2 = time.perf_counter()

    payload_size_kb = len(
        json.dumps(safe_plots, default=str).encode("utf-8")
    ) / 1024

    print(
        f"[DEBUG][plots] state={state} "
        f"total={total} returned={len(safe_plots)} "
        f"limit={limit} offset={offset} | "
        f"fetch={(t1 - t0)*1000:.2f} ms | "
        f"slice+sanitize={(t2 - t1)*1000:.2f} ms | "
        f"payload={payload_size_kb:.1f} KB"
    )

    return {
        "meta": {
            "total": total,
            "returned": len(safe_plots),
            "limit": limit,
            "offset": offset
        },
        "data": safe_plots
    }

@app.get("/api/{state}/pois")
def pois(state: str):
    return json_safe(cache["states"].get(state, {}).get("pois", []))


@app.get("/api/{state}/policy/search")
def policy_search(state: str, q: str):
    return search_policy(q, state)

@app.get("/api/{state}/pois/nearby")
def pois_nearby(
    state: str,
    lat: float,
    lng: float,
    radius_km: float = 10,
    poi_type: str | None = None
):
    return find_nearby_pois(state, lat, lng, radius_km, poi_type)
