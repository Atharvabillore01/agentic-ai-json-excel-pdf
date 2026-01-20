"""
Data mapping utilities for case-insensitive field access.
Helps handle different column naming conventions across sources.
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class CaseInsensitiveDict(dict):
    """Dictionary with case-insensitive key access"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key_map = {k.lower(): k for k in self.keys() if isinstance(k, str)}
    
    def __getitem__(self, key):
        if isinstance(key, str):
            actual_key = self._key_map.get(key.lower(), key)
            return super().__getitem__(actual_key)
        return super().__getitem__(key)
    
    def __setitem__(self, key, value):
        if isinstance(key, str):
            self._key_map[key.lower()] = key
        return super().__setitem__(key, value)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


def normalize_field_name(field: str) -> str:
    """Normalize field name to lowercase and strip whitespace"""
    if isinstance(field, str):
        return field.lower().strip()
    return str(field)


def get_field_value(
    record: Dict[str, Any],
    possible_field_names: List[str],
    default: Any = None,
    normalize: bool = True,
) -> Any:
    """
    Get value from record using multiple possible field names (case-insensitive).
    
    Args:
        record: Dictionary to search
        possible_field_names: List of possible field names to try
        default: Default value if not found
        normalize: Whether to normalize the field names
    
    Returns:
        Field value or default
    """
    # Create lowercase mapping of record keys
    record_lower = {k.lower() if isinstance(k, str) else k: v for k, v in record.items()}
    
    for field_name in possible_field_names:
        search_key = normalize_field_name(field_name) if normalize else field_name
        if search_key in record_lower:
            value = record_lower[search_key]
            # Skip None and NaN values
            import pandas as pd
            if value is not None and not pd.isna(value):
                return value
    
    return default


def normalize_record(
    record: Dict[str, Any],
    field_mapping: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Normalize record by mapping multiple possible field names to standard names.
    
    Args:
        record: Original record with various field names
        field_mapping: Dict mapping standard names to list of possible source names
        
    Example:
        field_mapping = {
            "park_name": ["park_name", "park_nm", "parkname"],
            "district": ["district", "dist_name", "dist", "dist_nm"]
        }
    
    Returns:
        Normalized record with standard field names
    """
    normalized = {}
    
    for standard_name, possible_names in field_mapping.items():
        value = get_field_value(record, possible_names)
        if value is not None:
            normalized[standard_name] = value
    
    # Include any unmapped fields that aren't already mapped
    record_lower_keys = {k.lower(): k for k in record.keys() if isinstance(k, str)}
    for original_key in record.keys():
        if isinstance(original_key, str):
            key_lower = original_key.lower()
            # Only add if not already mapped
            if not any(key_lower == p.lower() for possible_names in field_mapping.values() for p in possible_names):
                normalized[original_key] = record[original_key]
    
    return normalized


# Standard field mappings
PARK_FIELD_MAPPING = {
    "park_name": ["park_name", "park_nm", "parkname", "name"],
    "district": ["district", "dist_name", "dist", "dist_nm"],
    "sector": ["sector", "sec", "sector_type"],
    "status": ["status", "park_status", "st"],
    "_id": ["_id", "id", "park_id"],
}

PLOT_FIELD_MAPPING = {
    "plot_number": ["plot_number", "plotno", "plot_no", "plotnumber", "plot_num"],
    "park_name": ["park_name", "park_nm"],
    "park_id": ["park_id", "parkid", "park_id_ref"],
    "size_sq_m": ["size_sq_m", "plotsize", "plot_size", "size", "area"],
    "rate": ["rate", "plotrate", "plot_rate", "price", "cost"],
    "status": ["status", "plotstatus", "plot_status", "st"],
}

POI_FIELD_MAPPING = {
    "name": ["name", "poi_name", "feature_name"],
    "type": ["type", "poi_type", "category"],
    "distance_km": ["distance_km", "distance", "dist_km"],
    "geometry": ["geometry", "geom", "location"],
}


def normalize_park(park: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize park data with standard field names"""
    return normalize_record(park, PARK_FIELD_MAPPING)


def normalize_plot(plot: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize plot data with standard field names"""
    return normalize_record(plot, PLOT_FIELD_MAPPING)


def normalize_poi(poi: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize POI data with standard field names"""
    return normalize_record(poi, POI_FIELD_MAPPING)
