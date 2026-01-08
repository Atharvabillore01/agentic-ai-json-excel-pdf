from app.core.cache import cache
from app.vectorstore.policy_index import search_policy
from app.services.poi_distance import find_nearby_pois

def tool_search_policy(state: str, query: str):
    return search_policy(query, state)

def tool_get_parks(state: str, limit: int = 10):
    parks = cache["states"][state]["parks"][:limit]
    return [
        {
            "park_name": p.get("park_name"),
            "district": p.get("district"),
            "sector": p.get("sector"),
            "status": p.get("status")
        }
        for p in parks
    ]

def tool_get_plots(state: str, limit: int = 10):
    plots = cache["states"][state]["plots"][:limit]
    return [
        {
            "plot_number": p.get("plot_number"),
            "park_name": p.get("park_name"),
            "size_sq_m": p.get("size_sq_m"),
            "rate": p.get("rate"),
            "status": p.get("status")
        }
        for p in plots
    ]

def tool_find_nearby_pois(state: str, lat, lng, radius_km=20, poi_type=None):
    return find_nearby_pois(state, lat, lng, radius_km, poi_type)
