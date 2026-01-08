tools = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search industrial policy with citations",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": { "type": "string" },
                    "query": { "type": "string" }
                },
                "required": ["state", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_parks",
            "description": "Get industrial parks in a state",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": { "type": "string" },
                    "limit": { "type": "number" }
                },
                "required": ["state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_plots",
            "description": "Get industrial plots in a state",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": { "type": "string" },
                    "limit": { "type": "number" }
                },
                "required": ["state"]
            }
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
                    "state": { "type": "string" },
                    "lat": { "type": "number" },
                    "lng": { "type": "number" },
                    "radius_km": { "type": "number" },
                    "poi_type": { "type": "string" }
                },
                "required": ["state", "lat", "lng"]
            }
        }
    }
]
