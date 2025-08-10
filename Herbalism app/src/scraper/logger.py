"""
Structured logging and error handling utilities for the scraper system.

This module provides comprehensive logging capabilities with specialized error
categorization, debug file output, and detailed context preservation. Ensures
no errors are hidden and provides full traceability for debugging production
issues and system monitoring.
"""
import logging
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorCategory(Enum):
    """Categories for error classification and monitoring."""
    AI_PARSING = "ai_parsing"
    DATABASE = "database"
    VALIDATION = "validation"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class LogLevel(Enum):
    """Log levels with explicit severity mapping."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorContext:
    """Structured error context for comprehensive debugging."""
    timestamp: datetime
    category: ErrorCategory
    operation: str
    error_message: str
    stack_trace: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ScraperLogger:
    """
    Comprehensive logging service for scraper operations.
    
    Provides structured error logging with categorization, debug file output,
    and context preservation. All errors are logged with full detail to ensure
    complete traceability and no information loss.
    """
    
    def __init__(self, log_directory: str = "logs", debug_mode: bool = True):
        """
        Initialize scraper logger with file and console output.
        
        Args:
            log_directory: Directory for log files
            debug_mode: Enable debug-level logging and detailed output
        """
        self.log_directory = Path(log_directory)
        self.debug_mode = debug_mode
        self.error_history: List[ErrorContext] = []
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(exist_ok=True)
        
        # Configure Python logging
        self._setup_logging()
        
        self.logger = logging.getLogger(f"{__name__}.ScraperLogger")
        self.logger.info("ScraperLogger initialized")
    
    def log_ai_parsing_error(self, operation: str, input_text: str, ai_response: str, 
                           error: Exception, additional_context: Optional[Dict[str, Any]] = None):
        """
        Log AI parsing errors with complete context for debugging.
        
        Captures all details needed to reproduce and debug AI parsing failures,
        including full input text, AI response, and error context.
        
        Args:
            operation: Type of parsing operation (e.g., "recipe_parsing", "herb_extraction")
            input_text: Original text sent to AI
            ai_response: Raw response from AI service
            error: Exception that occurred
            additional_context: Additional debugging information
        """
        context_data = {
            "input_length": len(input_text),
            "input_preview": input_text[:200] + "..." if len(input_text) > 200 else input_text,
            "ai_response_length": len(ai_response),
            "ai_response": ai_response,
            "error_type": type(error).__name__,
            "error_details": str(error)
        }
        
        if additional_context:
            context_data.update(additional_context)
        
        error_context = ErrorContext(
            timestamp=datetime.now(),
            category=ErrorCategory.AI_PARSING,
            operation=operation,
            error_message=f"AI parsing failed: {str(error)}",
            stack_trace=traceback.format_exc(),
            additional_data=context_data
        )
        
        self._log_error_context(error_context)
        
        # Save full AI interaction to debug file
        if self.debug_mode:
            self._save_ai_debug_file(operation, input_text, ai_response, error, context_data)
    
    def log_database_error(self, operation: str, sql_query: Optional[str], 
                          data: Dict[str, Any], error: Exception,
                          additional_context: Optional[Dict[str, Any]] = None):
        """
        Log database operation errors with SQL context.
        
        Captures database errors with full SQL context, data being processed,
        and transaction state information for debugging.
        
        Args:
            operation: Database operation type (e.g., "recipe_insert", "herb_update")
            sql_query: SQL query that failed (if available)
            data: Data being processed when error occurred
            error: Database exception
            additional_context: Additional debugging information
        """
        context_data = {
            "sql_query": sql_query,
            "data_keys": list(data.keys()) if data else [],
            "data_sample": {k: str(v)[:100] for k, v in (data or {}).items()},
            "error_type": type(error).__name__,
            "error_details": str(error)
        }
        
        if additional_context:
            context_data.update(additional_context)
        
        error_context = ErrorContext(
            timestamp=datetime.now(),
            category=ErrorCategory.DATABASE,
            operation=operation,
            error_message=f"Database operation failed: {str(error)}",
            stack_trace=traceback.format_exc(),
            additional_data=context_data
        )
        
        self._log_error_context(error_context)
    
    def log_validation_error(self, operation: str, data_type: str, validation_failures: List[str],
                           data: Dict[str, Any], additional_context: Optional[Dict[str, Any]] = None):
        """
        Log validation errors with detailed field-level information.
        
        Captures validation failures with complete data context to help
        identify patterns and improve validation rules.
        
        Args:
            operation: Validation operation (e.g., "recipe_validation", "herb_safety_check")
            data_type: Type of data being validated
            validation_failures: List of specific validation failures
            data: Data that failed validation
            additional_context: Additional context
        """
        context_data = {
            "data_type": data_type,
            "validation_failures": validation_failures,
            "failure_count": len(validation_failures),
            "data_keys": list(data.keys()) if data else [],
            "data_preview": {k: str(v)[:100] for k, v in (data or {}).items()}
        }
        
        if additional_context:
            context_data.update(additional_context)
        
        error_context = ErrorContext(
            timestamp=datetime.now(),
            category=ErrorCategory.VALIDATION,
            operation=operation,
            error_message=f"Validation failed: {len(validation_failures)} issues found",
            additional_data=context_data
        )
        
        self._log_error_context(error_context)
    
    def log_network_error(self, operation: str, url: str, error: Exception,
                         response_data: Optional[Dict[str, Any]] = None,
                         additional_context: Optional[Dict[str, Any]] = None):
        """
        Log network operation errors with request/response context.
        
        Captures network failures with full request context for debugging
        connectivity and API issues.
        
        Args:
            operation: Network operation (e.g., "page_fetch", "robots_check")
            url: URL that failed
            error: Network exception
            response_data: Response information if available
            additional_context: Additional context
        """
        context_data = {
            "url": url,
            "error_type": type(error).__name__,
            "error_details": str(error),
            "response_data": response_data or {}
        }
        
        if additional_context:
            context_data.update(additional_context)
        
        error_context = ErrorContext(
            timestamp=datetime.now(),
            category=ErrorCategory.NETWORK,
            operation=operation,
            error_message=f"Network operation failed: {str(error)}",
            stack_trace=traceback.format_exc(),
            additional_data=context_data
        )
        
        self._log_error_context(error_context)
    
    def log_configuration_error(self, component: str, setting: str, error: Exception,
                               current_config: Optional[Dict[str, Any]] = None):
        """
        Log configuration errors with system context.
        
        Args:
            component: Component with configuration issue
            setting: Specific setting that failed
            error: Configuration error
            current_config: Current configuration state
        """
        context_data = {
            "component": component,
            "setting": setting,
            "error_type": type(error).__name__,
            "error_details": str(error),
            "current_config": current_config or {}
        }
        
        error_context = ErrorContext(
            timestamp=datetime.now(),
            category=ErrorCategory.CONFIGURATION,
            operation="configuration_check",
            error_message=f"Configuration error in {component}.{setting}: {str(error)}",
            stack_trace=traceback.format_exc(),
            additional_data=context_data
        )
        
        self._log_error_context(error_context)
    
    def log_operation_success(self, operation: str, duration_seconds: float,
                            results: Dict[str, Any], additional_context: Optional[Dict[str, Any]] = None):
        """
        Log successful operations for monitoring and performance tracking.
        
        Args:
            operation: Operation that succeeded
            duration_seconds: Time taken for operation
            results: Summary of operation results
            additional_context: Additional context
        """
        context_data = {
            "duration_seconds": duration_seconds,
            "results": results
        }
        
        if additional_context:
            context_data.update(additional_context)
        
        self.logger.info(f"Operation '{operation}' completed successfully in {duration_seconds:.2f}s",
                        extra={"context": context_data})
        
        # Log to debug file if enabled
        if self.debug_mode:
            self._save_debug_entry("success", operation, context_data)
    
    def log_operation_warning(self, operation: str, warning_message: str,
                            context: Optional[Dict[str, Any]] = None):
        """
        Log operation warnings that don't prevent completion.
        
        Args:
            operation: Operation that generated warning
            warning_message: Warning message
            context: Additional context
        """
        context_data = context or {}
        
        self.logger.warning(f"Operation '{operation}' warning: {warning_message}",
                          extra={"context": context_data})
        
        if self.debug_mode:
            self._save_debug_entry("warning", operation, {
                "warning_message": warning_message,
                **context_data
            })
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics for monitoring."""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Group by category
        category_counts = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Recent errors (last 24 hours)
        recent_cutoff = datetime.now().timestamp() - (24 * 3600)
        recent_errors = [e for e in self.error_history 
                        if e.timestamp.timestamp() > recent_cutoff]
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors_24h": len(recent_errors),
            "errors_by_category": category_counts,
            "most_common_error": max(category_counts.items(), 
                                   key=lambda x: x[1])[0] if category_counts else None,
            "latest_error": {
                "timestamp": self.error_history[-1].timestamp.isoformat(),
                "category": self.error_history[-1].category.value,
                "operation": self.error_history[-1].operation,
                "message": self.error_history[-1].error_message[:100]
            } if self.error_history else None
        }
    
    def get_recent_errors(self, limit: int = 10, category: Optional[ErrorCategory] = None) -> List[Dict[str, Any]]:
        """Get recent errors for debugging."""
        errors = self.error_history
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        recent = errors[-limit:] if errors else []
        
        return [
            {
                "timestamp": error.timestamp.isoformat(),
                "category": error.category.value,
                "operation": error.operation,
                "message": error.error_message,
                "has_stack_trace": bool(error.stack_trace),
                "context_keys": list(error.additional_data.keys()) if error.additional_data else []
            }
            for error in recent
        ]
    
    def export_debug_data(self, output_file: str, include_stack_traces: bool = True):
        """Export all debug data to file for analysis."""
        debug_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_errors": len(self.error_history),
            "errors": []
        }
        
        for error in self.error_history:
            error_data = asdict(error)
            error_data["timestamp"] = error.timestamp.isoformat()
            error_data["category"] = error.category.value
            
            if not include_stack_traces:
                error_data.pop("stack_trace", None)
            
            debug_data["errors"].append(error_data)
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Debug data exported to {output_path}")
    
    def _setup_logging(self):
        """Configure Python logging with file and console handlers."""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # File handler for all logs
        log_file = self.log_directory / "scraper.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        
        # Error file handler for errors only
        error_file = self.log_directory / "scraper_errors.log"
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and above to console
        console_handler.setFormatter(console_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        
        # Clear existing handlers and add ours
        root_logger.handlers = []
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)
    
    def _log_error_context(self, error_context: ErrorContext):
        """Log error context to all configured outputs."""
        # Add to history
        self.error_history.append(error_context)
        
        # Log to Python logging system
        self.logger.error(
            f"[{error_context.category.value}] {error_context.operation}: {error_context.error_message}",
            extra={
                "context": error_context.additional_data,
                "stack_trace": error_context.stack_trace
            }
        )
        
        # Save detailed debug information if enabled
        if self.debug_mode:
            self._save_error_debug_file(error_context)
        
        # Cleanup history if it gets too large
        if len(self.error_history) > 10000:
            self.error_history = self.error_history[-5000:]
    
    def _save_ai_debug_file(self, operation: str, input_text: str, ai_response: str,
                          error: Exception, context: Dict[str, Any]):
        """Save AI interaction details to debug file."""
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "input_text": input_text,
            "ai_response": ai_response,
            "context": context
        }
        
        debug_file = self.log_directory / f"ai_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    
    def _save_error_debug_file(self, error_context: ErrorContext):
        """Save detailed error context to debug file."""
        debug_data = asdict(error_context)
        debug_data["timestamp"] = error_context.timestamp.isoformat()
        debug_data["category"] = error_context.category.value
        
        debug_file = self.log_directory / f"error_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    
    def _save_debug_entry(self, entry_type: str, operation: str, data: Dict[str, Any]):
        """Save general debug entry to debug file."""
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "operation": operation,
            "data": data
        }
        
        debug_file = self.log_directory / f"debug_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(debug_data, ensure_ascii=False) + '\n')