import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger(__name__)


class DashboardManager:
    def __init__(self) -> None:
        self.stats = {
            "total_queries": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "requests_by_hour": defaultdict(int),
            "errors": [],
        }
    
    def record_query(self, success: bool, time_taken: float, error: Optional[str] = None) -> None:
        self.stats["total_queries"] += 1
        if success:
            self.stats["successful"] += 1
        else:
            self.stats["failed"] += 1
            if error:
                self.stats["errors"].append({
                    "error": error,
                    "time": datetime.now().isoformat(),
                })
        
        self.stats["total_time"] += time_taken
        
        hour = datetime.now().hour
        self.stats["requests_by_hour"][hour] += 1
    
    def get_stats(self) -> dict:
        avg_time = (
            self.stats["total_time"] / self.stats["total_queries"]
            if self.stats["total_queries"] > 0
            else 0
        )
        success_rate = (
            self.stats["successful"] / self.stats["total_queries"] * 100
            if self.stats["total_queries"] > 0
            else 0
        )
        
        return {
            "total_queries": self.stats["total_queries"],
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "avg_time": avg_time,
            "success_rate": success_rate,
            "requests_by_hour": dict(self.stats["requests_by_hour"]),
            "recent_errors": self.stats["errors"][-5:],
        }
    
    def reset_stats(self) -> None:
        self.stats = {
            "total_queries": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "requests_by_hour": defaultdict(int),
            "errors": [],
        }


class MetricsCollector:
    def __init__(self) -> None:
        self.metrics = defaultdict(list)
    
    def record(self, metric_name: str, value: float) -> None:
        self.metrics[metric_name].append({
            "value": value,
            "time": time.time(),
        })
    
    def get(self, metric_name: str) -> list:
        return self.metrics.get(metric_name, [])
    
    def avg(self, metric_name: str) -> float:
        values = [m["value"] for m in self.metrics.get(metric_name, [])]
        return sum(values) / len(values) if values else 0.0