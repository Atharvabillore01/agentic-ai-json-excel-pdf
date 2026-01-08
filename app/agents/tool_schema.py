tools = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search industrial policy with citations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string" }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_parks",
            "description": "Get all industrial parks in the state",
            "parameters": { "type": "object", "properties": {} }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_plots",
            "description": "Get all plots in the state",
            "parameters": { "type": "object", "properties": {} }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby_pois",
            "description": "Find nearby infrastructure like stations, airports",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": { "type": "number" },
                    "lng": { "type": "number" },
                    "radius_km": { "type": "number" },
                    "poi_type": { "type": "string" }
                },
                "required": ["lat", "lng"]
            }
        }
    }
]
