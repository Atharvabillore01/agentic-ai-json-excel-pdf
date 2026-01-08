from app.core.cache import cache
from app.vectorstore.policy_index import search_policy
from app.services.poi_distance import find_nearby_pois

def tool_search_policy(state: str, query: str):
    return search_policy(query, state)

def tool_get_parks(state: str):
    return cache["states"][state]["parks"]

def tool_get_plots(state: str):
    return cache["states"][state]["plots"]

def tool_find_nearby_pois(state: str, lat, lng, radius_km=20, poi_type=None):
    return find_nearby_pois(state, lat, lng, radius_km, poi_type)
