"""
Enhanced logging and observability for debugging and monitoring.
"""
import logging
import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import traceback

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@dataclass
class RequestLog:
    """Log entry for a request"""
    request_id: str
    timestamp: str
    state: str
    question: str
    response_length: int
    execution_time: float
    tools_used: List[str]
    success: bool
    error: Optional[str] = None
    confidence_score: Optional[float] = None
    data_sources: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RequestLogger:
    """Logs and tracks individual requests"""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.logger = logging.getLogger(f"request.{request_id}")
        self.events: List[Dict[str, Any]] = []
        self.data_sources: List[str] = []
        self.tools_used: List[str] = []
        
        self.log_event("request_started", {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        level: str = "INFO"
    ) -> None:
        """Log an event during request processing"""
        timestamp = datetime.utcnow().isoformat()
        elapsed = time.time() - self.start_time
        
        event = {
            "event_type": event_type,
            "timestamp": timestamp,
            "elapsed_ms": round(elapsed * 1000, 2),
            "details": details
        }
        
        self.events.append(event)
        
        log_msg = f"[{event_type}] {json.dumps(details)}"
        
        if level == "DEBUG":
            self.logger.debug(log_msg)
        elif level == "WARNING":
            self.logger.warning(log_msg)
        elif level == "ERROR":
            self.logger.error(log_msg)
        else:
            self.logger.info(log_msg)
    
    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result_count: int,
        execution_time: float,
    ) -> None:
        """Log a tool execution"""
        self.tools_used.append(tool_name)
        self.log_event("tool_call", {
            "tool": tool_name,
            "args": arguments,
            "result_count": result_count,
            "execution_time_ms": round(execution_time * 1000, 2)
        })
    
    def log_data_source(self, source_name: str, count: int) -> None:
        """Log retrieved data sources"""
        self.data_sources.append(source_name)
        self.log_event("data_source", {
            "source": source_name,
            "count": count
        })
    
    def log_validation(
        self,
        is_valid: bool,
        confidence: float,
        issues: List[str],
        warnings: List[str],
    ) -> None:
        """Log validation result"""
        self.log_event("validation", {
            "is_valid": is_valid,
            "confidence": confidence,
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "issues": issues[:3],  # Log first 3
            "warnings": warnings[:3]  # Log first 3
        })
    
    def log_error(self, error: Exception) -> None:
        """Log an error"""
        self.log_event("error", {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        }, level="ERROR")
    
    def get_request_log(
        self,
        state: str,
        question: str,
        response: str,
        success: bool,
        confidence_score: Optional[float] = None,
        error: Optional[str] = None,
    ) -> RequestLog:
        """Generate request log entry"""
        execution_time = time.time() - self.start_time
        
        return RequestLog(
            request_id=self.request_id,
            timestamp=datetime.utcnow().isoformat(),
            state=state,
            question=question,
            response_length=len(response),
            execution_time=round(execution_time, 2),
            tools_used=self.tools_used,
            success=success,
            error=error,
            confidence_score=confidence_score,
            data_sources=self.data_sources
        )
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get all events for this request"""
        return self.events


class PerformanceMonitor:
    """Monitor system performance"""
    
    def __init__(self):
        self.tool_times: Dict[str, List[float]] = {}
        self.request_times: List[float] = []
        self.validation_times: List[float] = []
    
    def record_tool_time(self, tool_name: str, duration: float) -> None:
        """Record tool execution time"""
        if tool_name not in self.tool_times:
            self.tool_times[tool_name] = []
        self.tool_times[tool_name].append(duration)
    
    def record_request_time(self, duration: float) -> None:
        """Record full request time"""
        self.request_times.append(duration)
    
    def record_validation_time(self, duration: float) -> None:
        """Record validation time"""
        self.validation_times.append(duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        def _avg(times):
            return sum(times) / len(times) if times else 0
        
        def _max(times):
            return max(times) if times else 0
        
        stats = {
            "tools": {},
            "requests": {
                "total": len(self.request_times),
                "avg_time_ms": round(_avg(self.request_times) * 1000, 2),
                "max_time_ms": round(_max(self.request_times) * 1000, 2),
            },
            "validation": {
                "total": len(self.validation_times),
                "avg_time_ms": round(_avg(self.validation_times) * 1000, 2),
            }
        }
        
        for tool_name, times in self.tool_times.items():
            stats["tools"][tool_name] = {
                "calls": len(times),
                "avg_time_ms": round(_avg(times) * 1000, 2),
                "max_time_ms": round(_max(times) * 1000, 2),
            }
        
        return stats


class AuditLogger:
    """Audit trail for compliance and debugging"""
    
    def __init__(self):
        self.audit_log = logging.getLogger("audit")
        self.entries: List[Dict[str, Any]] = []
    
    def log_request(
        self,
        user_id: Optional[str],
        state: str,
        question: str,
        response: str,
        confidence: float,
        success: bool,
    ) -> None:
        """Log a request for audit trail"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id or "anonymous",
            "state": state,
            "question_length": len(question),
            "response_length": len(response),
            "confidence": confidence,
            "success": success,
        }
        
        self.entries.append(entry)
        self.audit_log.info(json.dumps(entry))
    
    def get_audit_summary(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit entries"""
        return self.entries[-limit:]


def create_debug_report(
    request_log: RequestLog,
    event_log: List[Dict[str, Any]],
    validation_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create comprehensive debug report"""
    report = {
        "request": request_log.to_dict(),
        "timeline": event_log,
        "summary": {
            "total_events": len(event_log),
            "tools_used": request_log.tools_used,
            "success": request_log.success,
            "duration_seconds": request_log.execution_time,
            "confidence_score": request_log.confidence_score,
        }
    }
    
    if validation_result:
        report["validation"] = validation_result
    
    return report


# Global instances
_performance_monitor = PerformanceMonitor()
_audit_logger = AuditLogger()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    return _performance_monitor


def get_audit_logger() -> AuditLogger:
    """Get global audit logger"""
    return _audit_logger


def log_to_file(
    filename: str,
    data: Dict[str, Any],
) -> None:
    """Save log data to file"""
    try:
        with open(filename, 'a') as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        logger.error(f"Failed to write log file {filename}: {e}")
