from app.core.cache import cache
from app.utils.geo import haversine

def find_nearby_pois(state, lat, lng, radius_km=10, poi_type=None):
    results = []

    pois = cache["states"].get(state, {}).get("pois", [])

    for poi in pois:
        coords = poi.get("geometry", {}).get("coordinates")
        if not coords or len(coords) != 2:
            continue

        poi_lng, poi_lat = coords
        dist = haversine(lat, lng, poi_lat, poi_lng)

        if dist <= radius_km:
            if poi_type and poi.get("properties", {}).get("poiType") != poi_type:
                continue

            results.append({
                "name": poi.get("properties", {}).get("name"),
                "type": poi.get("properties", {}).get("poiType"),
                "distance_km": round(dist, 2),
                "location": {
                    "lat": poi_lat,
                    "lng": poi_lng
                }
            })

    return sorted(results, key=lambda x: x["distance_km"])
