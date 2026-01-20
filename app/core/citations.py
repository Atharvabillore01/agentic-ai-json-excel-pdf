"""
Citation tracking and source verification to prevent hallucinations.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
import re
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation in a response"""
    source_id: str
    source_name: str
    page: int
    section: Optional[str] = None
    quote: Optional[str] = None
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceVerification:
    """Result of source verification"""
    is_verifiable: bool
    citations: List[Citation]
    verified_count: int
    unverified_count: int
    confidence_score: float


class CitationTracker:
    """Tracks and verifies citations in agent responses"""
    
    def __init__(self):
        self.verified_sources: Dict[str, Dict[str, Any]] = {}
        self.response_citations: List[Citation] = []
    
    def register_source(
        self,
        source_id: str,
        source_name: str,
        page: int,
        content: str,
        section: Optional[str] = None,
    ) -> None:
        """Register a source that can be cited"""
        if source_id not in self.verified_sources:
            self.verified_sources[source_id] = {
                "name": source_name,
                "page": page,
                "section": section,
                "content": content,
                "key_terms": self._extract_key_terms(content),
            }
    
    def _extract_key_terms(self, content: str, top_n: int = 20) -> Set[str]:
        """Extract key terms from content"""
        # Remove common words
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "are", "be", "been", "was",
            "were", "that", "this", "these", "those", "it", "its", "he", "she",
            "they", "them", "their", "we", "us", "our", "you", "your", "i", "me"
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]{4,}\b', content.lower())
        key_terms = [w for w in words if w not in common_words]
        
        # Count frequency
        term_freq = {}
        for term in key_terms:
            term_freq[term] = term_freq.get(term, 0) + 1
        
        # Return top terms
        sorted_terms = sorted(term_freq.items(), key=lambda x: x[1], reverse=True)
        return set(term[0] for term in sorted_terms[:top_n])
    
    def verify_citations_in_response(
        self,
        response: str,
        policy_chunks: List[Dict[str, Any]],
    ) -> SourceVerification:
        """
        Verify that response citations are backed by policy chunks.
        
        Args:
            response: Agent response text
            policy_chunks: Available policy chunks
        
        Returns:
            SourceVerification with citation details
        """
        citations = []
        verified_count = 0
        
        # Register available sources
        for chunk in policy_chunks:
            self.register_source(
                source_id=chunk.get("id", "unknown"),
                source_name=chunk.get("source", "unknown"),
                page=chunk.get("page", 0),
                content=chunk.get("text", ""),
                section=chunk.get("section"),
            )
        
        # Extract citation claims from response
        citation_claims = self._extract_citation_claims(response)
        
        # Verify each claim against sources
        for claim in citation_claims:
            verified_sources = self._find_supporting_sources(claim)
            
            if verified_sources:
                verified_count += 1
                for source_id in verified_sources:
                    source = self.verified_sources[source_id]
                    citations.append(Citation(
                        source_id=source_id,
                        source_name=source["name"],
                        page=source["page"],
                        section=source.get("section"),
                        relevance_score=0.8,
                    ))
        
        unverified_count = len(citation_claims) - verified_count
        confidence = verified_count / len(citation_claims) if citation_claims else 1.0
        
        return SourceVerification(
            is_verifiable=verified_count == len(citation_claims),
            citations=citations,
            verified_count=verified_count,
            unverified_count=unverified_count,
            confidence_score=min(1.0, confidence),
        )
    
    def _extract_citation_claims(self, response: str) -> List[str]:
        """Extract claims that might need citation"""
        claims = []
        
        # Look for common citation markers
        patterns = [
            r"(?:according to|as per|government states|policy requires|must)\s+([^.!?\n]{20,100})",
            r"([A-Z][a-z\s]{10,100}(?:policy|act|regulation|rule|scheme))",
            r"(?:The )?([A-Z][a-z\s]{10,50})\s+(?:is|are|requires|provides|offers)",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                claim = match.group(1).strip()
                if len(claim) > 10:
                    claims.append(claim)
        
        return list(set(claims))  # Remove duplicates
    
    def _find_supporting_sources(self, claim: str) -> List[str]:
        """Find sources that support a claim"""
        supporting = []
        
        claim_terms = set(re.findall(r'\b[a-z]{3,}\b', claim.lower()))
        
        for source_id, source_info in self.verified_sources.items():
            source_terms = source_info["key_terms"]
            overlap = len(claim_terms & source_terms)
            
            # If 50%+ of claim terms are in source, it likely supports the claim
            if overlap / len(claim_terms) > 0.5:
                supporting.append(source_id)
        
        return supporting
    
    def add_citations_to_response(
        self,
        response: str,
        citations: List[Citation],
    ) -> str:
        """Add citation metadata to response"""
        citation_text = ""
        
        if citations:
            citation_text = "\n\n**Sources:**\n"
            for i, citation in enumerate(citations, 1):
                cite = (
                    f"{i}. {citation.source_name} "
                    f"(page {citation.page})"
                )
                if citation.section:
                    cite += f" - Section: {citation.section}"
                citation_text += cite + "\n"
        
        return response + citation_text


class SourceDocumentation:
    """Documents all sources used in reasoning"""
    
    def __init__(self):
        self.sources_used: List[Dict[str, Any]] = []
        self.tools_called: List[Dict[str, Any]] = []
        self.reasoning_steps: List[Dict[str, Any]] = []
    
    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        results: Any,
        sources_referenced: Optional[List[str]] = None,
    ) -> None:
        """Record a tool call and its sources"""
        self.tools_called.append({
            "tool": tool_name,
            "arguments": arguments,
            "result_count": len(results) if isinstance(results, list) else 1,
            "sources": sources_referenced or [],
        })
        
        # Track sources
        if sources_referenced:
            for source in sources_referenced:
                if source not in [s["id"] for s in self.sources_used]:
                    self.sources_used.append({"id": source})
    
    def add_reasoning_step(
        self,
        step: int,
        description: str,
        tools_used: Optional[List[str]] = None,
        conclusion: Optional[str] = None,
    ) -> None:
        """Record a reasoning step"""
        self.reasoning_steps.append({
            "step": step,
            "description": description,
            "tools_used": tools_used or [],
            "conclusion": conclusion,
        })
    
    def get_documentation(self) -> Dict[str, Any]:
        """Get full source documentation"""
        return {
            "sources_used": self.sources_used,
            "tools_called": self.tools_called,
            "reasoning_steps": self.reasoning_steps,
            "total_sources": len(self.sources_used),
            "total_tools": len(self.tools_called),
        }


class HalluccinationDetector:
    """Detects potential hallucinations in responses"""
    
    HALLUCINATION_PATTERNS = [
        # Uncertain language indicating speculation
        (r"\b(?:might|could|possibly|probably|seems to|appears to|likely)\b", "speculation"),
        # Claims without evidence markers
        (r"\b(?:I believe|I think|I assume|in my opinion)\b", "opinion"),
        # Contradictions to facts
        (r"\b(?:although|however|but actually)\b.*(?:not|no|never)\b", "contradiction"),
        # Made-up specifics
        (r"(?:approximately|roughly|around)\s+\d+%", "vague_specificity"),
    ]
    
    @staticmethod
    def score_hallucination_risk(
        response: str,
        citations: List[Citation],
    ) -> Tuple[float, List[str]]:
        """
        Score hallucination risk (0.0 = safe, 1.0 = high risk).
        
        Returns:
            Tuple of (risk_score, risk_indicators)
        """
        risk_score = 0.0
        indicators = []
        
        # Check for suspicious patterns
        for pattern, risk_type in HalluccinationDetector.HALLUCINATION_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                risk_score += 0.15
                indicators.append(f"Potential {risk_type} detected")
        
        # Low citation backing
        if not citations:
            risk_score += 0.3
            indicators.append("No citations provided")
        elif len(citations) < 2 and len(response) > 500:
            risk_score += 0.15
            indicators.append("Insufficient citations for response length")
        
        # Long unsupported claims
        sentences = re.split(r'[.!?]', response)
        unsupported_long_claims = sum(
            1 for s in sentences 
            if len(s.strip()) > 200
        )
        if unsupported_long_claims > 0:
            risk_score += unsupported_long_claims * 0.1
            indicators.append(f"Found {unsupported_long_claims} long unsupported claims")
        
        return min(1.0, risk_score), indicators
