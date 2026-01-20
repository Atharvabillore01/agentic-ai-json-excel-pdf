"""
Response validation pipeline for ensuring accuracy and preventing hallucinations.
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ResponseValidationResult:
    """Result of response validation"""
    is_valid: bool
    confidence_score: float
    hallucination_risk: float
    hallucination_indicators: List[str]
    citation_coverage: float
    data_alignment_score: float
    completeness_score: float
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]


class ResponseValidationPipeline:
    """Multi-stage validation of responses"""
    
    def __init__(self):
        self.validators = [
            self._check_hallucination_risk,
            self._check_citation_coverage,
            self._check_data_alignment,
            self._check_factual_claims,
            self._check_completeness,
        ]
    
    def validate_response(
        self,
        response: str,
        user_question: str,
        retrieved_data: Dict[str, Any],
        available_parks: List[Dict[str, Any]],
        available_plots: List[Dict[str, Any]],
    ) -> ResponseValidationResult:
        """
        Validate response through multiple stages.
        
        Args:
            response: Agent's response text
            user_question: Original user question
            retrieved_data: Data retrieved by tools
            available_parks: All available parks
            available_plots: All available plots
        
        Returns:
            ResponseValidationResult with validation details
        """
        issues = []
        warnings = []
        recommendations = []
        scores = {
            "hallucination_risk": 0.0,
            "citation_coverage": 0.0,
            "data_alignment": 0.0,
            "completeness": 0.0,
        }
        hallucination_indicators = []
        
        # Run all validators
        
        # 1. Hallucination Risk
        hal_risk, hal_indicators = self._check_hallucination_risk(
            response, retrieved_data
        )
        scores["hallucination_risk"] = hal_risk
        hallucination_indicators.extend(hal_indicators)
        
        # 2. Citation Coverage
        cit_coverage, cit_issues = self._check_citation_coverage(
            response, retrieved_data
        )
        scores["citation_coverage"] = cit_coverage
        if cit_issues:
            issues.extend(cit_issues)
        
        # 3. Data Alignment
        data_align, data_issues = self._check_data_alignment(
            response, retrieved_data, available_parks, available_plots
        )
        scores["data_alignment"] = data_align
        if data_issues:
            issues.extend(data_issues)
        
        # 4. Factual Claims
        fact_issues, fact_warnings = self._check_factual_claims(
            response, available_parks
        )
        if fact_issues:
            issues.extend(fact_issues)
        if fact_warnings:
            warnings.extend(fact_warnings)
        
        # 5. Completeness
        completeness, completeness_issues = self._check_completeness(
            response, user_question
        )
        scores["completeness"] = completeness
        if completeness_issues:
            recommendations.extend(completeness_issues)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(scores, len(issues))
        
        # Determine validity
        is_valid = (
            scores["hallucination_risk"] < 0.6 and
            scores["data_alignment"] > 0.5 and
            len(issues) == 0
        )
        
        return ResponseValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            hallucination_risk=scores["hallucination_risk"],
            hallucination_indicators=hallucination_indicators,
            citation_coverage=scores["citation_coverage"],
            data_alignment_score=scores["data_alignment"],
            completeness_score=scores["completeness"],
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
        )
    
    def _check_hallucination_risk(
        self,
        response: str,
        retrieved_data: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Check for hallucination risk"""
        risk_score = 0.0
        indicators = []
        
        # Check 1: Uncertain language
        uncertain_words = [
            r"\bmight\b", r"\bcould\b", r"\bprobably\b",
            r"\bseems\b", r"\bappears\b", r"\blikely\b",
            r"\bpresumably\b", r"\bgenerally\b", r"\busually\b"
        ]
        
        uncertain_count = 0
        for word_pattern in uncertain_words:
            matches = len(re.findall(word_pattern, response, re.IGNORECASE))
            uncertain_count += matches
        
        if uncertain_count > 0:
            risk_score += min(0.3, uncertain_count * 0.05)
            indicators.append(
                f"Found {uncertain_count} instances of uncertain language"
            )
        
        # Check 2: Claims without data backing
        policy_count = len(retrieved_data.get("policies", []))
        parks_count = len(retrieved_data.get("parks", []))
        plots_count = len(retrieved_data.get("plots", []))
        
        if not retrieved_data or (policy_count == 0 and parks_count == 0):
            risk_score += 0.4
            indicators.append("Response without retrieved data backing")
        
        # Check 3: Generic/vague statements
        generic_patterns = [
            r"(?:various|several|multiple|many)\s+(?:parks|plots|policies)",
            r"(?:in general|typically|as a rule)",
        ]
        
        generic_count = sum(
            len(re.findall(p, response, re.IGNORECASE))
            for p in generic_patterns
        )
        
        if generic_count > 0:
            risk_score += min(0.2, generic_count * 0.1)
            indicators.append(f"Found {generic_count} generic/vague statements")
        
        # Check 4: Numerical claims
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|km|sq\.?m|acres|rupees?)?\b', response)
        if numbers and policy_count == 0:
            risk_score += 0.15
            indicators.append(
                f"Numerical claims without policy backing: {numbers[:3]}"
            )
        
        return min(1.0, risk_score), indicators
    
    def _check_citation_coverage(
        self,
        response: str,
        retrieved_data: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Check if response is adequately cited"""
        issues = []
        
        # Count citation indicators
        citation_indicators = [
            "according to", "as per", "policy", "government",
            "scheme", "act", "regulation", "data shows"
        ]
        
        citation_count = sum(
            len(re.findall(f"\\b{ind}\\b", response, re.IGNORECASE))
            for ind in citation_indicators
        )
        
        response_length = len(response.split())
        
        # Acceptable ratio: 1 citation per ~150 words
        expected_citations = max(1, response_length // 150)
        coverage = min(1.0, citation_count / max(1, expected_citations))
        
        if coverage < 0.5:
            issues.append(
                f"Low citation coverage: {citation_count} citations for "
                f"~{response_length} words"
            )
        
        return coverage, issues
    
    def _check_data_alignment(
        self,
        response: str,
        retrieved_data: Dict[str, Any],
        available_parks: List[Dict[str, Any]],
        available_plots: List[Dict[str, Any]],
    ) -> Tuple[float, List[str]]:
        """Check if response aligns with retrieved data"""
        issues = []
        alignment_score = 1.0
        
        # Extract park names mentioned in response
        response_lower = response.lower()
        park_mentions = []
        
        for park in available_parks:
            park_name = park.get("park_name", "").lower()
            if park_name and park_name in response_lower:
                park_mentions.append(park_name)
        
        # If response mentions parks, they should exist in our data
        if "park" in response_lower:
            retrieved_parks = retrieved_data.get("parks", [])
            if retrieved_parks:
                retrieved_park_names = {
                    p.get("park_name", "").lower()
                    for p in retrieved_parks
                }
                
                if park_mentions:
                    alignment = len(park_mentions) / max(1, len(park_mentions) + 3)
                    alignment_score *= alignment
                else:
                    # Mentions parks but doesn't name specific ones
                    alignment_score *= 0.7
            else:
                alignment_score *= 0.6
                if "park" in response_lower and not park_mentions:
                    issues.append("Response mentions parks without specific names")
        
        # Check plot mentions
        if "plot" in response_lower:
            retrieved_plots = retrieved_data.get("plots", [])
            if not retrieved_plots:
                alignment_score *= 0.7
                issues.append("Response mentions plots but no plot data was retrieved")
        
        return alignment_score, issues
    
    def _check_factual_claims(
        self,
        response: str,
        available_parks: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[str]]:
        """Check for verifiable factual claims"""
        issues = []
        warnings = []
        
        # Extract numbers and specific claims
        numbers = re.findall(r'\b(\d+)\s+(parks?|plots?|acres?|sq\.?m)', response, re.IGNORECASE)
        
        if numbers:
            total_parks = len(available_parks)
            for num_str, entity in numbers:
                try:
                    num = int(num_str)
                    if "park" in entity.lower() and num > total_parks * 1.5:
                        warnings.append(
                            f"Claimed {num} parks but only {total_parks} in database"
                        )
                except ValueError:
                    pass
        
        # Check for industry-specific claims without backing
        industry_patterns = [
            r"(?:auto|automotive|manufacturing|pharma|textiles?)\s+(?:sector|industry|hub)",
        ]
        
        for pattern in industry_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                # These should reference policies or parks
                if "policy" not in response.lower() and "park" not in response.lower():
                    warnings.append(
                        f"Industry claim without policy or park backing"
                    )
        
        return issues, warnings
    
    def _check_completeness(
        self,
        response: str,
        user_question: str,
    ) -> Tuple[float, List[str]]:
        """Check if response adequately answers the question"""
        issues = []
        completeness = 1.0
        
        # Extract key question terms
        question_words = set(
            w.lower() for w in user_question.split()
            if len(w) > 3
        )
        
        response_lower = response.lower()
        covered_terms = sum(
            1 for term in question_words
            if term in response_lower
        )
        
        coverage_ratio = covered_terms / max(1, len(question_words))
        completeness = coverage_ratio
        
        if coverage_ratio < 0.3:
            issues.append(
                f"Response covers only {coverage_ratio:.1%} of question terms"
            )
        
        # Check for common question types
        if "what" in user_question.lower() or "which" in user_question.lower():
            if not any(word in response_lower for word in ["no", "not available", "unknown"]):
                if len(response.split()) < 50:
                    issues.append("Very short response to information request")
        
        if "how" in user_question.lower() or "why" in user_question.lower():
            if response_lower.count("because") == 0:
                completeness *= 0.8
                issues.append("Question asks for explanation but response is incomplete")
        
        return completeness, issues
    
    def _calculate_confidence(
        self,
        scores: Dict[str, float],
        issue_count: int,
    ) -> float:
        """Calculate overall confidence score"""
        base_confidence = 0.7
        
        # Hallucination risk reduces confidence
        base_confidence -= scores["hallucination_risk"] * 0.3
        
        # Good data alignment increases confidence
        base_confidence += scores["data_alignment"] * 0.15
        
        # Citation coverage increases confidence
        base_confidence += scores["citation_coverage"] * 0.1
        
        # Completeness helps
        base_confidence += scores["completeness"] * 0.1
        
        # Issues reduce confidence
        base_confidence -= min(0.3, issue_count * 0.05)
        
        return max(0.0, min(1.0, base_confidence))


def validate_and_fix_response(
    response: str,
    user_question: str,
    retrieved_data: Dict[str, Any],
    available_parks: List[Dict[str, Any]],
    available_plots: List[Dict[str, Any]],
) -> Tuple[str, ResponseValidationResult]:
    """
    Validate response and apply fixes if needed.
    
    Returns:
        Tuple of (possibly_fixed_response, validation_result)
    """
    pipeline = ResponseValidationPipeline()
    
    validation = pipeline.validate_response(
        response,
        user_question,
        retrieved_data,
        available_parks,
        available_plots,
    )
    
    # Log validation results
    if validation.issues:
        logger.warning(f"Validation issues: {validation.issues}")
    
    if validation.warnings:
        logger.warning(f"Validation warnings: {validation.warnings}")
    
    if validation.recommendations:
        logger.info(f"Recommendations: {validation.recommendations}")
    
    # Apply basic fixes
    fixed_response = response
    
    # Fix 1: Remove uncertain language if confidence is low
    if validation.hallucination_risk > 0.7:
        uncertain_replacements = {
            r"\bmight\b": "could",
            r"\bseems to\b": "appears to",
            r"\bprobably\b": "",  # Remove entirely
            r"\blikely\b": "",
        }
        
        for pattern, replacement in uncertain_replacements.items():
            if replacement == "":
                fixed_response = re.sub(
                    pattern, "", fixed_response, flags=re.IGNORECASE
                )
            else:
                fixed_response = re.sub(
                    pattern, replacement, fixed_response, flags=re.IGNORECASE
                )
    
    # Fix 2: Add confidence disclaimer if needed
    if validation.confidence_score < 0.6:
        disclaimer = (
            "\n\n**Note**: This response has moderate confidence. "
            "Some information could not be fully verified with available data."
        )
        fixed_response += disclaimer
    
    return fixed_response, validation
