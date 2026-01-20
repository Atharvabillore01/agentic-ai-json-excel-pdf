"""
Fact Verification System - Ensures no hallucination of critical data
Validates distances, prices, coordinates, and availability claims
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Types of data that require verification"""
    DISTANCE = "distance"
    PRICE = "price"
    COORDINATE = "coordinate"
    AVAILABILITY = "availability"
    INFRASTRUCTURE = "infrastructure"
    GENERAL = "general"


class VerificationLevel(Enum):
    """Verification strictness levels"""
    STRICT = "strict"  # Never provide unverified specific data
    MODERATE = "moderate"  # Provide if context available
    RELAXED = "relaxed"  # Provide with disclaimer


class FactVerifier:
    """Verifies factual claims against available data"""
    
    def __init__(self, verification_level: VerificationLevel = VerificationLevel.STRICT):
        """
        Initialize fact verifier
        
        Args:
            verification_level: How strict to be with verification
        """
        self.verification_level = verification_level
        logger.info(f"FactVerifier initialized with {verification_level.value} verification")
    
    def verify_distance_claim(self, distance: str, from_point: str, to_point: str) -> Dict:
        """
        Verify a distance claim
        
        Args:
            distance: Claimed distance (e.g., "5 km")
            from_point: Starting point (e.g., "plot XYZ")
            to_point: Ending point (e.g., "railway station")
        
        Returns:
            Dictionary with verification status
        """
        return {
            "claim_type": "distance",
            "claim": f"{distance} from {from_point} to {to_point}",
            "verified": False,
            "reason": "Distance claims require verified coordinates and cannot be estimated",
            "action": "Ask user for specific plot details and verify with GPS/mapping data",
            "data_required": ["exact_plot_name", "exact_location", "destination_name"],
            "confidence": 0.0
        }
    
    def verify_price_claim(self, price: str, plot_size: str, area: str) -> Dict:
        """
        Verify a price claim
        
        Args:
            price: Claimed price
            plot_size: Plot size
            area: Area name
        
        Returns:
            Dictionary with verification status
        """
        return {
            "claim_type": "price",
            "claim": f"₹{price} for {plot_size} in {area}",
            "verified": False,
            "reason": "Price claims are market-dependent and change frequently",
            "action": "Provide only if exact data exists in current database",
            "data_required": ["exact_plot_id", "current_market_data", "transaction_date"],
            "confidence": 0.0,
            "disclaimer": "This is indicative only. Actual prices may vary based on plot condition, location within park, and current market."
        }
    
    def verify_coordinate_claim(self, lat: str, lng: str, location: str) -> Dict:
        """
        Verify a coordinate claim
        
        Args:
            lat: Latitude
            lng: Longitude
            location: Location name
        
        Returns:
            Dictionary with verification status
        """
        return {
            "claim_type": "coordinate",
            "claim": f"Coordinates for {location}",
            "verified": False,
            "reason": "Coordinates must be verified against official maps",
            "action": "Only provide if coordinates are in verified database",
            "data_required": ["verified_gps_data", "official_source"],
            "confidence": 0.0
        }
    
    def verify_availability_claim(self, plot_id: str, status: str, timestamp: str = None) -> Dict:
        """
        Verify an availability claim
        
        Args:
            plot_id: Plot identifier
            status: Claimed status (available/unavailable)
            timestamp: When data was last updated
        
        Returns:
            Dictionary with verification status
        """
        return {
            "claim_type": "availability",
            "claim": f"Plot {plot_id} is {status}",
            "verified": False,
            "reason": "Availability changes and requires real-time verification",
            "action": "Query live database, not estimates",
            "data_required": ["real_time_database", "current_status_check"],
            "confidence": 0.0,
            "disclaimer": "Please verify current availability with the authorities as status changes frequently."
        }
    
    def verify_infrastructure_claim(self, claim: str, infrastructure_type: str) -> Dict:
        """
        Verify infrastructure proximity claim
        
        Args:
            claim: The claim about infrastructure
            infrastructure_type: Type of infrastructure (railway, highway, airport, etc.)
        
        Returns:
            Dictionary with verification status
        """
        return {
            "claim_type": "infrastructure",
            "claim": claim,
            "infrastructure": infrastructure_type,
            "verified": False,
            "reason": "Infrastructure proximity requires verified distance data",
            "action": "Ask for specific plot details to verify against known infrastructure locations",
            "data_required": ["specific_plot_location", "infrastructure_name", "verified_distance"],
            "confidence": 0.0
        }
    
    def categorize_data_type(self, text: str) -> DataType:
        """
        Categorize what type of data a text contains
        
        Args:
            text: Text to categorize
        
        Returns:
            DataType classification
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["distance", "km", "kilometers", "away from", "proximity", "miles"]):
            return DataType.DISTANCE
        
        if any(word in text_lower for word in ["price", "cost", "rupees", "rs", "₹", "per acre", "rate"]):
            return DataType.PRICE
        
        if any(word in text_lower for word in ["coordinate", "latitude", "longitude", "lat", "lng", "°"]):
            return DataType.COORDINATE
        
        if any(word in text_lower for word in ["available", "stock", "current status", "vacant", "occupied"]):
            return DataType.AVAILABILITY
        
        if any(word in text_lower for word in ["railway", "airport", "highway", "station", "port", "infrastructure"]):
            return DataType.INFRASTRUCTURE
        
        return DataType.GENERAL
    
    def should_require_user_input(self, data_type: DataType) -> bool:
        """
        Determine if user input should be required for this data type
        
        Args:
            data_type: Type of data
        
        Returns:
            True if user input should be required
        """
        sensitive_types = [
            DataType.DISTANCE,
            DataType.PRICE,
            DataType.COORDINATE,
            DataType.AVAILABILITY
        ]
        return data_type in sensitive_types
    
    def should_request_verification(self, claim: str) -> Tuple[bool, str]:
        """
        Check if a claim should request verification
        
        Args:
            claim: The claim to check
        
        Returns:
            Tuple of (should_verify, reason)
        """
        data_type = self.categorize_data_type(claim)
        
        if data_type == DataType.DISTANCE:
            return True, "Distance claims must be verified with exact plot coordinates"
        
        if data_type == DataType.PRICE:
            return True, "Price claims must be verified against current market data"
        
        if data_type == DataType.COORDINATE:
            return True, "Coordinates must be verified from official sources"
        
        if data_type == DataType.AVAILABILITY:
            return True, "Availability must be verified in real-time"
        
        if data_type == DataType.INFRASTRUCTURE:
            return True, "Infrastructure proximity must be verified with specific locations"
        
        return False, ""
    
    def build_verification_response(self, claim: str, data_type: DataType) -> Dict:
        """
        Build a response for an unverified claim
        
        Args:
            claim: The claim
            data_type: Type of data
        
        Returns:
            Dictionary with recommended response
        """
        responses = {
            DataType.DISTANCE: {
                "type": "ask_for_details",
                "message": "To provide accurate distance information, I need the following:",
                "required_inputs": [
                    "Exact plot name or identification number",
                    "Specific location within the industrial park",
                    "Which infrastructure point? (e.g., 'XYZ Railway Station', 'ABC Airport Terminal')"
                ],
                "reason": "I cannot estimate distances without verified coordinates"
            },
            DataType.PRICE: {
                "type": "ask_for_details",
                "message": "I can help with pricing information if you provide:",
                "required_inputs": [
                    "Desired plot size (in acres or sq. m)",
                    "Preferred location/sector",
                    "Are you looking for current market rate or historical data?",
                    "Investment timeline?"
                ],
                "reason": "Prices are dynamic and require current market data"
            },
            DataType.COORDINATE: {
                "type": "limit_response",
                "message": "Specific coordinates are available, but I need to verify them from official sources",
                "required_inputs": [
                    "Plot identification number",
                    "Industrial park name",
                    "Official survey document reference"
                ],
                "reason": "Coordinates must come from verified official sources"
            },
            DataType.AVAILABILITY: {
                "type": "refer_to_system",
                "message": "For real-time availability, please use our plot search system or contact the industrial park authority",
                "required_inputs": [],
                "reason": "Availability status changes frequently"
            },
            DataType.INFRASTRUCTURE: {
                "type": "ask_for_details",
                "message": "To verify infrastructure proximity, I need:",
                "required_inputs": [
                    "Specific plot location/name",
                    "Which infrastructure? (exact name of railway station/airport/highway)",
                    "Purpose? (for travel time, logistics planning, etc.)"
                ],
                "reason": "Proximity claims require verified coordinates and infrastructure locations"
            }
        }
        
        return responses.get(data_type, {
            "type": "general",
            "message": "I don't have sufficient verified data to answer this accurately",
            "reason": "Cannot determine without additional information"
        })
    
    def generate_disclaimer(self, data_types_used: List[DataType]) -> str:
        """
        Generate a disclaimer based on data types used
        
        Args:
            data_types_used: List of data types used in response
        
        Returns:
            Appropriate disclaimer
        """
        disclaimers = []
        
        if DataType.DISTANCE in data_types_used:
            disclaimers.append("Distance information is indicative and based on available maps. Please verify with ground surveys.")
        
        if DataType.PRICE in data_types_used:
            disclaimers.append("Prices are subject to change and market conditions. Please confirm current rates with authorities.")
        
        if DataType.COORDINATE in data_types_used:
            disclaimers.append("Coordinates should be verified with official surveys before any transactions.")
        
        if DataType.AVAILABILITY in data_types_used:
            disclaimers.append("Availability status changes frequently. Please verify current status before making decisions.")
        
        if not disclaimers:
            return ""
        
        return "⚠️ **DISCLAIMERS**:\n" + "\n".join(f"• {d}" for d in disclaimers)


# Singleton instance
_verifier = None

def get_fact_verifier(verification_level: VerificationLevel = VerificationLevel.STRICT) -> FactVerifier:
    """Get or create fact verifier singleton"""
    global _verifier
    if _verifier is None:
        _verifier = FactVerifier(verification_level)
    return _verifier
