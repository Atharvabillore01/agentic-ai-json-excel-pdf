"""
Data validation and error handling to prevent hallucinations and bad data.
"""
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of validation process"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class DataIntegrityValidator:
    """Validates data integrity to prevent hallucinations"""
    
    @staticmethod
    def validate_park_data(park: Dict[str, Any]) -> ValidationResult:
        """Validate park object structure and required fields"""
        errors = []
        warnings = []
        
        # Normalize keys to lowercase for matching
        park_lower = {k.lower() if isinstance(k, str) else k: v for k, v in park.items()}
        
        # Required fields (check multiple possible names)
        required_checks = [
            (['park_name', 'park_nm'], "park name"),
            (['district', 'dist_name', 'dist', 'dist_nm'], "district"),
        ]
        
        for field_names, field_desc in required_checks:
            found = False
            for field in field_names:
                if field in park_lower and park_lower[field]:
                    found = True
                    break
            if not found:
                errors.append(f"Missing required field: {field_desc}")
        
        # Field type validation
        if 'park_name' in park_lower and not isinstance(park_lower.get('park_name'), (str, type(None))):
            warnings.append("park_name should be string")
        
        if 'status' in park_lower:
            valid_statuses = ["operational", "under_development", "planned", "parsing", "waiting"]
            status_val = str(park_lower['status']).lower()
            if status_val not in valid_statuses:
                warnings.append(f"Unusual status: {status_val}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=1.0 - (len(errors) * 0.2)
        )
    
    @staticmethod
    def validate_plot_data(plot: Dict[str, Any]) -> ValidationResult:
        """Validate plot object structure"""
        errors = []
        warnings = []
        
        # Normalize keys to lowercase for matching
        plot_lower = {k.lower() if isinstance(k, str) else k: v for k, v in plot.items()}
        
        # Required fields (check multiple possible names)
        required_checks = [
            (['plot_number', 'plotno', 'plot_no', 'plotnumber'], "plot number"),
            (['park_name', 'park_id', 'parkid', 'park_nm'], "park reference"),
        ]
        
        for field_names, field_desc in required_checks:
            found = False
            for field in field_names:
                if field in plot_lower and plot_lower[field]:
                    found = True
                    break
            if not found:
                errors.append(f"Missing required field: {field_desc}")
        
        # Numeric validation
        size_fields = ['size_sq_m', 'plotsize', 'plot_size', 'size']
        for size_field in size_fields:
            if size_field in plot_lower and plot_lower[size_field]:
                try:
                    size = float(plot_lower[size_field])
                    if size <= 0:
                        errors.append("size must be positive")
                    break
                except (ValueError, TypeError):
                    pass
        
        rate_fields = ['rate', 'plotrate', 'plot_rate', 'price']
        for rate_field in rate_fields:
            if rate_field in plot_lower and plot_lower[rate_field]:
                try:
                    rate = float(plot_lower[rate_field])
                    if rate < 0:
                        errors.append("rate must be non-negative")
                    break
                except (ValueError, TypeError):
                    pass
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=1.0 - (len(errors) * 0.2)
        )
    
    @staticmethod
    def validate_policy_chunk(chunk: Dict[str, Any]) -> ValidationResult:
        """Validate policy chunk structure"""
        errors = []
        warnings = []
        
        required_fields = ["text", "source", "page"]
        for field in required_fields:
            if not chunk.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check text is not empty
        if chunk.get("text"):
            text_len = len(chunk["text"].strip())
            if text_len < 10:
                warnings.append("Policy text is very short")
            if text_len > 50000:
                warnings.append("Policy chunk is very large")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class ResponseValidator:
    """Validates agent responses against available data"""
    
    @staticmethod
    def validate_park_claims(
        response: str, 
        available_parks: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Check if response mentions parks that actually exist"""
        errors = []
        warnings = []
        
        park_names = {p.get("park_name", "").lower() for p in available_parks}
        
        # Simple heuristic: check for specific park mentions
        response_lower = response.lower()
        mentioned_parks = []
        for park_name in park_names:
            if park_name and park_name in response_lower:
                mentioned_parks.append(park_name)
        
        # If response mentions parks but we can't verify all, add warning
        if "park" in response_lower and not mentioned_parks:
            warnings.append("Response mentions parks but doesn't cite specific ones")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=min(1.0, 0.7 + (len(mentioned_parks) * 0.1))
        )
    
    @staticmethod
    def validate_citation_claims(
        response: str,
        policy_chunks: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Validate that cited policies exist in sources"""
        errors = []
        warnings = []
        
        # Extract potential citations from response (simplified)
        sources = {c.get("source", "") for c in policy_chunks if c.get("source")}
        pages = {str(c.get("page", "")) for c in policy_chunks if c.get("page")}
        
        # Check if response claims to cite policies
        citation_indicators = ["according to", "policy states", "government", "as per"]
        has_citations = any(ind in response.lower() for ind in citation_indicators)
        
        if has_citations and not policy_chunks:
            errors.append("Response claims policy citations but no policies available")
        
        if has_citations and policy_chunks:
            # Good - citations are supported by available data
            pass
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def check_hallucination_markers(response: str) -> ValidationResult:
        """Check response for common hallucination patterns"""
        errors = []
        warnings = []
        
        hallucination_markers = [
            ("imaginary", "Potentially invented"),
            ("reportedly", "Unverified claim"),
            ("probably means", "Speculation"),
            ("i assume", "Unsupported assumption"),
            ("it is likely", "Unfounded projection"),
        ]
        
        response_lower = response.lower()
        found_markers = []
        
        for marker, desc in hallucination_markers:
            if marker in response_lower:
                found_markers.append(desc)
        
        if found_markers:
            warnings.extend(found_markers)
        
        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings,
            confidence_score=max(0.3, 1.0 - (len(warnings) * 0.15))
        )


class StateValidator:
    """Validate state-related inputs"""
    
    @staticmethod
    def validate_state(state: str, available_states: List[str]) -> ValidationResult:
        """Validate state exists in system"""
        errors = []
        warnings = []
        
        normalized_state = state.lower().replace(" ", "_")
        
        if normalized_state not in available_states:
            errors.append(f"Unknown state: {state}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class ToolResultValidator:
    """Validate tool execution results"""
    
    @staticmethod
    def validate_search_results(
        results: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Validate policy search results"""
        errors = []
        warnings = []
        
        if not isinstance(results, list):
            errors.append("Search results must be a list")
        
        if len(results) == 0:
            warnings.append("No results found for search query")
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"Result {i} is not a dictionary")
                continue
            
            validation = DataIntegrityValidator.validate_policy_chunk(result)
            if not validation.is_valid:
                errors.extend([f"Result {i}: {e}" for e in validation.errors])
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=max(0.0, 1.0 - (len(errors) * 0.1))
        )
    
    @staticmethod
    def validate_list_results(
        results: List[Dict[str, Any]],
        expected_type: str = "generic"
    ) -> ValidationResult:
        """Validate list-type results (parks, plots, etc)"""
        errors = []
        warnings = []
        
        if not isinstance(results, list):
            errors.append("Results must be a list")
            return ValidationResult(is_valid=False, errors=errors)
        
        if len(results) == 0:
            warnings.append("Empty result list")
        
        # Validate each item
        validator_map = {
            "park": DataIntegrityValidator.validate_park_data,
            "plot": DataIntegrityValidator.validate_plot_data,
        }
        
        validator_func = validator_map.get(expected_type)
        
        if validator_func:
            for i, item in enumerate(results):
                validation = validator_func(item)
                if not validation.is_valid:
                    errors.extend([f"Item {i}: {e}" for e in validation.errors])
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=max(0.0, 1.0 - (len(errors) * 0.05))
        )


def validate_and_log(
    validation_result: ValidationResult,
    context: str = "validation"
) -> bool:
    """Log validation results and return validity status"""
    if validation_result.errors:
        logger.error(f"[{context}] Validation errors: {validation_result.errors}")
    
    if validation_result.warnings:
        logger.warning(f"[{context}] Warnings: {validation_result.warnings}")
    
    if validation_result.confidence_score < 0.5:
        logger.warning(
            f"[{context}] Low confidence score: {validation_result.confidence_score}"
        )
    
    return validation_result.is_valid
