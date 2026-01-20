"""
Response Categorizer - Separates responses into verified/user-input/unavailable
Ensures no hallucination of factual data
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseCategory:
    """Container for categorized response sections"""
    
    def __init__(self):
        self.verified_information: List[str] = []
        self.requires_user_input: List[str] = []
        self.unavailable_data: List[str] = []
        self.sources: List[str] = []
        self.follow_up_questions: List[str] = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "verified_information": self.verified_information,
            "requires_user_input": self.requires_user_input,
            "unavailable_data": self.unavailable_data,
            "sources": self.sources,
            "follow_up_questions": self.follow_up_questions
        }
    
    def has_verified_info(self) -> bool:
        """Check if there's any verified information"""
        return len(self.verified_information) > 0
    
    def requires_input(self) -> bool:
        """Check if user input is needed"""
        return len(self.requires_user_input) > 0
    
    def has_unavailable(self) -> bool:
        """Check if there's data that cannot be determined"""
        return len(self.unavailable_data) > 0


class ResponseCategorizer:
    """Categorizes responses into strict verification categories"""
    
    # Patterns that indicate specific quantitative data
    DISTANCE_PATTERNS = [
        r"(?:distance|km|kilometers|miles|proximity|away from)",
        r"(?:\d+\s*(?:km|km\.?|kilometers?|miles?|m|meters?|feet?))",
    ]
    
    PRICE_PATTERNS = [
        r"(?:price|cost|rate|rupees?|rs\.?|₹|per acre|per sq|price tag)",
        r"(?:₹\s*\d+|rs\.\s*\d+)",
    ]
    
    COORDINATE_PATTERNS = [
        r"(?:latitude|longitude|coordinates|lat|lng|°)",
        r"(?:\d+\.?\d*°\s*[NS].*?\d+\.?\d*°\s*[EW])",
    ]
    
    AVAILABILITY_PATTERNS = [
        r"(?:available|stock|plot\s+(?:number|no|#)|currently)",
        r"(?:\d+\s+plots?\s+available|in stock)",
    ]
    
    # Patterns indicating data cannot be determined
    UNCERTAIN_PATTERNS = [
        r"(?:don'?t have\s+(?:sufficient|exact|specific).*(?:data|information|details))",
        r"(?:cannot.*without\s+(?:external|additional|more))",
        r"(?:unclear|unknown|unverified|not available)",
        r"(?:would need to.*to determine)",
        r"(?:requires.*input|need.*details|provide.*information)",
    ]
    
    # Patterns indicating qualitative information (safe to provide)
    QUALITATIVE_PATTERNS = [
        r"(?:policy|incentive|investment climate|scheme|facility|advantage|benefit|opportunity)",
        r"(?:is (?:known for|famous for|considered)|generally|typically|commonly)",
        r"(?:compared to|versus|competitive|competitive advantage)",
    ]
    
    def __init__(self):
        """Initialize categorizer"""
        self.compiled_patterns = {
            "distance": [re.compile(p, re.IGNORECASE) for p in self.DISTANCE_PATTERNS],
            "price": [re.compile(p, re.IGNORECASE) for p in self.PRICE_PATTERNS],
            "coordinate": [re.compile(p, re.IGNORECASE) for p in self.COORDINATE_PATTERNS],
            "availability": [re.compile(p, re.IGNORECASE) for p in self.AVAILABILITY_PATTERNS],
            "uncertain": [re.compile(p, re.IGNORECASE) for p in self.UNCERTAIN_PATTERNS],
            "qualitative": [re.compile(p, re.IGNORECASE) for p in self.QUALITATIVE_PATTERNS],
        }
        logger.info("ResponseCategorizer initialized")
    
    def categorize(self, response_text: str) -> ResponseCategory:
        """
        Categorize response into verified/requires-input/unavailable
        
        Args:
            response_text: The response to categorize
        
        Returns:
            ResponseCategory with separated information
        """
        category = ResponseCategory()
        
        # Split response into sections if they exist
        sections = self._extract_sections(response_text)
        
        if sections.get("verified"):
            category.verified_information = self._extract_verified_claims(sections["verified"])
        
        if sections.get("requires_input"):
            category.requires_user_input = self._extract_requirements(sections["requires_input"])
        
        if sections.get("unavailable"):
            category.unavailable_data = self._extract_unavailable(sections["unavailable"])
        
        # Extract sources if mentioned
        category.sources = self._extract_sources(response_text)
        
        # Extract follow-up questions
        category.follow_up_questions = self._extract_follow_up_questions(response_text)
        
        logger.info(f"Categorized response: {len(category.verified_information)} verified, "
                   f"{len(category.requires_user_input)} require input, "
                   f"{len(category.unavailable_data)} unavailable")
        
        return category
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract predefined sections from response"""
        sections = {}
        
        # Pattern for section headers
        verified_match = re.search(
            r"(?:verified\s+information|verified\s+facts?|confirmed\s+data)[\s\n:]*(.+?)(?=\n\n|requires|unavailable|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if verified_match:
            sections["verified"] = verified_match.group(1).strip()
        
        requires_match = re.search(
            r"(?:requires?\s+user\s+input|requires?\s+information|missing\s+inputs?)[\s\n:]*(.+?)(?=\n\n|unavailable|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if requires_match:
            sections["requires_input"] = requires_match.group(1).strip()
        
        unavailable_match = re.search(
            r"(?:unavailable|cannot\s+be\s+determined|no\s+sufficient\s+data)[\s\n:]*(.+?)(?=\n\n|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if unavailable_match:
            sections["unavailable"] = unavailable_match.group(1).strip()
        
        return sections
    
    def _extract_verified_claims(self, text: str) -> List[str]:
        """Extract verified information claims"""
        claims = []
        
        # Split by bullets or lines
        lines = re.split(r"[\n•\-]", text)
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Only include if it doesn't match uncertain patterns
            if not any(p.search(line) for p in self.compiled_patterns["uncertain"]):
                claims.append(line)
        
        return claims[:10]  # Limit to 10 claims
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract requirements for user input"""
        requirements = []
        
        lines = re.split(r"[\n•\-]", text)
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                requirements.append(line)
        
        return requirements[:8]  # Limit to 8 requirements
    
    def _extract_unavailable(self, text: str) -> List[str]:
        """Extract unavailable information"""
        unavailable = []
        
        lines = re.split(r"[\n•\-]", text)
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                unavailable.append(line)
        
        return unavailable[:8]  # Limit to 8 items
    
    def _extract_sources(self, text: str) -> List[str]:
        """Extract source references"""
        sources = []
        
        # Look for common source patterns
        source_patterns = [
            r"(?:source|from|according to|cite|source:)\s*([^.\n]+)",
            r"\(([^)]*policy[^)]*)\)",
            r"(?:from |from )\s*([A-Z][a-zA-Z\s]+(?:\.pdf|policy|document))",
        ]
        
        for pattern in source_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            sources.extend(matches)
        
        return list(set(sources))[:5]  # Limit to 5 unique sources
    
    def _extract_follow_up_questions(self, text: str) -> List[str]:
        """Extract follow-up questions"""
        questions = []
        
        # Look for question patterns
        q_pattern = r"(?:would you|can you|do you|please.*?|could you.*?|to help.*?\?|[\?])"
        
        matches = re.findall(r"[^?.!]*\?", text)
        questions.extend([q.strip() for q in matches if q.strip() and len(q) > 10])
        
        return questions[:5]  # Limit to 5 questions
    
    def detect_factual_claims(self, text: str) -> Dict[str, List[str]]:
        """
        Detect specific factual claims that need verification
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary of factual claims by category
        """
        claims = {
            "distance_claims": [],
            "price_claims": [],
            "coordinate_claims": [],
            "availability_claims": [],
            "other_quantitative": [],
        }
        
        sentences = re.split(r"[.!?]\s+", text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # Check for distance claims
            if any(p.search(sentence) for p in self.compiled_patterns["distance"]):
                claims["distance_claims"].append(sentence.strip())
            
            # Check for price claims
            if any(p.search(sentence) for p in self.compiled_patterns["price"]):
                claims["price_claims"].append(sentence.strip())
            
            # Check for coordinate claims
            if any(p.search(sentence) for p in self.compiled_patterns["coordinate"]):
                claims["coordinate_claims"].append(sentence.strip())
            
            # Check for availability claims
            if any(p.search(sentence) for p in self.compiled_patterns["availability"]):
                claims["availability_claims"].append(sentence.strip())
            
            # Check for other quantitative claims
            if re.search(r"\d+\s*(?:%|acres?|sq\.?\s*m|slots?|slots)", sentence):
                claims["other_quantitative"].append(sentence.strip())
        
        logger.info(f"Detected {sum(len(v) for v in claims.values())} factual claims")
        return claims
    
    def is_response_safe(self, response_text: str) -> bool:
        """
        Check if response is safe (doesn't hallucinate facts)
        
        Args:
            response_text: Response to check
        
        Returns:
            True if safe, False if it contains hallucinated facts
        """
        # Check if response explicitly states limitations
        has_limitations = any(p.search(response_text) for p in self.compiled_patterns["uncertain"])
        
        # Check for factual claims without caveats
        factual_claims = self.detect_factual_claims(response_text)
        
        # If has specific quantitative claims but doesn't acknowledge limitations, it's risky
        has_quantitative = any(len(v) > 0 for v in factual_claims.values())
        
        if has_quantitative and not has_limitations:
            logger.warning("Response contains quantitative claims without disclaimers")
            return False
        
        return True
    
    def suggest_follow_ups(self, detected_claims: Dict[str, List[str]]) -> List[str]:
        """
        Suggest follow-up questions based on detected claims
        
        Args:
            detected_claims: Dictionary of detected claims
        
        Returns:
            List of suggested follow-up questions
        """
        suggestions = []
        
        if detected_claims.get("distance_claims"):
            suggestions.append("Could you provide the exact plot name or location to verify distance information?")
        
        if detected_claims.get("price_claims"):
            suggestions.append("What is your investment budget and plot size requirement for accurate pricing?")
        
        if detected_claims.get("availability_claims"):
            suggestions.append("Would you like to check specific plot availability with our system?")
        
        if detected_claims.get("coordinate_claims"):
            suggestions.append("Do you need GPS coordinates for site visits?")
        
        return suggestions[:3]  # Limit to 3 suggestions


# Singleton instance
_categorizer = None

def get_response_categorizer() -> ResponseCategorizer:
    """Get or create response categorizer singleton"""
    global _categorizer
    if _categorizer is None:
        _categorizer = ResponseCategorizer()
    return _categorizer
