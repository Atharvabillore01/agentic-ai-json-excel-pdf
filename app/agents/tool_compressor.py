"""
Smart compression of tool results while preserving important data.
"""
import json
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


def compress_tool_result(
    tool_name: str,
    result: Any,
    max_items: int = 5,
    max_chars: int = 1500,
) -> str:
    """
    Intelligently compress tool results for agent consumption.
    
    Preserves:
    - Most relevant data
    - Structural information
    - Metadata for verification
    
    Args:
        tool_name: Name of the tool called
        result: Result from tool execution
        max_items: Max items to include in lists
        max_chars: Max characters in output
    
    Returns:
        Compressed result string
    """
    if result is None:
        return f"{tool_name}: no result"

    if isinstance(result, list):
        return _compress_list_result(tool_name, result, max_items, max_chars)
    
    elif isinstance(result, dict):
        return _compress_dict_result(tool_name, result, max_chars)
    
    else:
        return str(result)[:max_chars]


def _compress_list_result(
    tool_name: str,
    results: List[Any],
    max_items: int,
    max_chars: int,
) -> str:
    """Compress list results with smart sampling"""
    
    if not results:
        return f"{tool_name}: empty result set"
    
    total = len(results)
    
    # Determine compression based on tool type
    if tool_name == "search_policy":
        return _compress_policy_results(results, max_items, max_chars)
    
    elif tool_name == "get_parks":
        return _compress_parks_results(results, max_items, max_chars)
    
    elif tool_name == "get_plots":
        return _compress_plots_results(results, max_items, max_chars)
    
    elif tool_name == "find_nearby_pois":
        return _compress_pois_results(results, max_items, max_chars)
    
    else:
        # Generic list compression
        sample = results[:max_items]
        text = f"{tool_name}: {total} total results.\n"
        for i, item in enumerate(sample, 1):
            text += f"{i}. {_format_item(item)}\n"
        return text[:max_chars]


def _compress_policy_results(
    results: List[Dict[str, Any]],
    max_items: int,
    max_chars: int,
) -> str:
    """Compress policy search results"""
    text = f"Found {len(results)} policy documents:\n\n"
    
    for i, chunk in enumerate(results[:max_items], 1):
        source = chunk.get("source", "unknown")
        page = chunk.get("page", "?")
        section = chunk.get("section", "")
        policy_text = chunk.get("text", "")
        
        # Extract first 150 chars or first sentence
        excerpt = policy_text[:180].split(". ")[0] + "..."
        
        text += f"{i}. **{source}** (Page {page})"
        if section:
            text += f" - Section: {section}"
        text += f"\n   {excerpt}\n\n"
    
    if len(results) > max_items:
        text += f"... and {len(results) - max_items} more results\n"
    
    return text[:max_chars]


def _compress_parks_results(
    results: List[Dict[str, Any]],
    max_items: int,
    max_chars: int,
) -> str:
    """Compress parks data with key details"""
    if not results:
        return "No parks found."
    
    text = f"Industrial Parks: {len(results)} total\n\n"
    
    # Group by status for better context
    status_groups: Dict[str, List[Dict[str, Any]]] = {}
    for park in results:
        # Get status from various possible field names
        status = park.get('status') or park.get('park_status') or 'unknown'
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(park)
    
    # Present by status
    for status, parks in sorted(status_groups.items()):
        text += f"**{status.title()}** ({len(parks)}):\n"
        
        for park in parks[:2]:  # Show top 2 per status
            name = park.get('park_name') or park.get('name') or 'Unknown'
            district = park.get('district') or park.get('dist_name') or ''
            sector = park.get('sector') or ''
            
            text += f"  • {name}"
            if district:
                text += f" ({district})"
            if sector:
                text += f" - {sector}"
            text += "\n"
        
        if len(parks) > 2:
            text += f"  ... +{len(parks) - 2} more\n"
        text += "\n"
    
    return text[:max_chars]


def _compress_plots_results(
    results: List[Dict[str, Any]],
    max_items: int,
    max_chars: int,
) -> str:
    """Compress plots data with key metrics"""
    if not results:
        return "No plots found."
    
    text = f"Available Plots: {len(results)} total\n\n"
    
    # Calculate summary stats
    sizes = []
    rates = []
    
    for plot in results:
        try:
            # Try multiple field names for size
            size_val = plot.get('size_sq_m') or plot.get('plotsize') or plot.get('size')
            if size_val:
                sizes.append(float(size_val))
            
            # Try multiple field names for rate
            rate_val = plot.get('rate') or plot.get('plotrate') or plot.get('price')
            if rate_val:
                rates.append(float(rate_val))
        except (ValueError, TypeError):
            pass
    
    # Summary stats
    if sizes:
        avg_size = sum(sizes) / len(sizes)
        text += f"Size Range: {min(sizes):.0f} - {max(sizes):.0f} sq.m (avg: {avg_size:.0f})\n"
    
    if rates:
        avg_rate = sum(rates) / len(rates)
        text += f"Rate Range: ₹{min(rates):.0f} - ₹{max(rates):.0f} per sq.m (avg: ₹{avg_rate:.0f})\n"
    
    text += f"\nSample Plots:\n"
    
    # Show sample plots
    for i, plot in enumerate(results[:max_items], 1):
        plot_num = plot.get('plot_number') or plot.get('plotno') or '?'
        park = plot.get('park_name') or '?'
        size = plot.get('size_sq_m') or plot.get('plotsize') or '?'
        rate = plot.get('rate') or plot.get('plotrate') or '?'
        status = plot.get('status') or plot.get('plotstatus') or '?'
        
        text += f"{i}. Plot {plot_num} in {park}: {size} sq.m @ ₹{rate}/sq.m ({status})\n"
    
    if len(results) > max_items:
        text += f"\n... {len(results) - max_items} more plots available\n"
    
    return text[:max_chars]


def _compress_pois_results(
    results: List[Dict[str, Any]],
    max_items: int,
    max_chars: int,
) -> str:
    """Compress POI (points of interest) results"""
    text = f"Infrastructure Points: {len(results)} nearby\n\n"
    
    # Group by type
    type_groups: Dict[str, List[Dict[str, Any]]] = {}
    for poi in results:
        props = poi.get("properties", {})
        poi_type = props.get("type", "other")
        if poi_type not in type_groups:
            type_groups[poi_type] = []
        type_groups[poi_type].append(poi)
    
    # Present by type
    for poi_type, pois in sorted(type_groups.items()):
        text += f"**{poi_type.title()}** ({len(pois)}):\n"
        
        for poi in pois[:2]:
            props = poi.get("properties", {})
            name = props.get("name", "Unknown")
            distance = props.get("distance_km", "?")
            text += f"  • {name} ({distance} km away)\n"
        
        if len(pois) > 2:
            text += f"  ... +{len(pois) - 2} more\n"
        text += "\n"
    
    return text[:max_chars]


def _compress_dict_result(
    tool_name: str,
    result: Dict[str, Any],
    max_chars: int,
) -> str:
    """Compress dictionary results"""
    text = ""
    
    # Extract key information
    for key, value in list(result.items())[:10]:  # Limit to 10 keys
        if isinstance(value, (str, int, float, bool)):
            text += f"{key}: {value}\n"
        elif isinstance(value, list) and len(value) > 0:
            text += f"{key}: {len(value)} items\n"
        elif isinstance(value, dict):
            text += f"{key}: (nested data)\n"
    
    return text[:max_chars]


def _format_item(item: Any) -> str:
    """Format a single item for display"""
    if isinstance(item, dict):
        # Try to extract key fields
        important_fields = ["name", "title", "park_name", "plot_number"]
        for field in important_fields:
            if field in item:
                return str(item[field])
        
        # Fallback to first few key-value pairs
        pairs = []
        for k, v in list(item.items())[:3]:
            if isinstance(v, str):
                pairs.append(f"{k}: {v}")
        return " | ".join(pairs) if pairs else str(item)
    
    return str(item)
