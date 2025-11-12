# modules/logger.py - Comprehensive Logging System

import traceback
from datetime import datetime
from typing import Optional

class Logger:
    """Handles all application logging with downloadable log file"""
    
    def __init__(self):
        self.logs = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0
    
    def _add_log(self, level: str, message: str, exception: Optional[Exception] = None):
        """Internal method to add log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'exception': None,
            'traceback': None
        }
        
        if exception:
            log_entry['exception'] = str(exception)
            log_entry['traceback'] = traceback.format_exc()
        
        self.logs.append(log_entry)
        
        # Update counters
        if level == "ERROR":
            self.error_count += 1
        elif level == "WARNING":
            self.warning_count += 1
        elif level == "INFO":
            self.info_count += 1
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log an error"""
        self._add_log("ERROR", message, exception)
        print(f"[ERROR] {message}")
        if exception:
            print(f"Exception: {exception}")
    
    def log_warning(self, message: str):
        """Log a warning"""
        self._add_log("WARNING", message)
        print(f"[WARNING] {message}")
    
    def log_info(self, message: str):
        """Log info"""
        self._add_log("INFO", message)
        print(f"[INFO] {message}")
    
    def has_errors(self) -> bool:
        """Check if any errors have been logged"""
        return self.error_count > 0
    
    def get_log_file(self) -> str:
        """Generate downloadable log file content"""
        lines = [
            "=" * 80,
            f"PCON Manifest System - Log File",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Logs: {len(self.logs)} (Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count})",
            "=" * 80,
            ""
        ]
        
        for log in self.logs:
            lines.append(f"[{log['timestamp']}] {log['level']}: {log['message']}")
            if log['exception']:
                lines.append(f"  Exception: {log['exception']}")
            if log['traceback']:
                lines.append(f"  Traceback:")
                for line in log['traceback'].split('\n'):
                    lines.append(f"    {line}")
            lines.append("")
        
        return "\n".join(lines)
    
    def clear_logs(self):
        """Clear all logs"""
        self.logs = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0
        self.log_info("Logs cleared")
    
    def get_recent_errors(self, count: int = 5) -> list:
        """Get recent error messages"""
        errors = [log for log in self.logs if log['level'] == "ERROR"]
        return errors[-count:] if errors else []
