"""Monitoring and metrics for the research system"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics tracked"""
    RESEARCH_TIME = "research_time"
    ANALYSIS_TIME = "analysis_time"
    WRITING_TIME = "writing_time"
    CRITIQUE_TIME = "critique_time"
    TOTAL_TIME = "total_time"
    REVISION_COUNT = "revision_count"
    QUALITY_SCORE = "quality_score"
    API_CALLS = "api_calls"
    TOKENS_USED = "tokens_used"
    COST = "cost"


@dataclass
class PhaseMetrics:
    """Metrics for a single phase"""
    phase_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    api_calls: int = 0
    tokens_used: int = 0
    
    def complete(self, status: str = "completed"):
        """Mark phase as complete"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = status
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'phase_name': self.phase_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status,
            'error': self.error,
            'api_calls': self.api_calls,
            'tokens_used': self.tokens_used
        }


@dataclass
class SessionMetrics:
    """Metrics for an entire research session"""
    session_id: str
    topic: str
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    phase_metrics: Dict[str, PhaseMetrics] = field(default_factory=dict)
    revision_count: int = 0
    final_quality_score: Optional[int] = None
    total_api_calls: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    
    def add_phase_metric(self, phase_name: str) -> PhaseMetrics:
        """Add a new phase metric"""
        metric = PhaseMetrics(phase_name, datetime.now())
        self.phase_metrics[phase_name] = metric
        return metric
    
    def get_total_duration(self) -> float:
        """Get total session duration in seconds"""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return (datetime.now() - self.created_at).total_seconds()
    
    def calculate_cost(self) -> float:
        """Calculate estimated API cost"""
        # Approximate costs per 1M tokens (as of 2024)
        gpt4o_mini_input = 0.15  # $0.15 per 1M input tokens
        gpt4o_mini_output = 0.60  # $0.60 per 1M output tokens
        
        # Rough estimate: 30% input, 70% output
        input_tokens = int(self.total_tokens * 0.3)
        output_tokens = int(self.total_tokens * 0.7)
        
        cost = (input_tokens * gpt4o_mini_input + 
                output_tokens * gpt4o_mini_output) / 1_000_000
        
        self.estimated_cost = cost
        return cost
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'topic': self.topic,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_seconds': self.get_total_duration(),
            'phase_metrics': {k: v.to_dict() for k, v in self.phase_metrics.items()},
            'revision_count': self.revision_count,
            'final_quality_score': self.final_quality_score,
            'total_api_calls': self.total_api_calls,
            'total_tokens': self.total_tokens,
            'estimated_cost': round(self.estimated_cost, 4)
        }


class MetricsCollector:
    """Collects and manages metrics for research sessions"""
    
    def __init__(self, metrics_file: str = "metrics.jsonl"):
        """Initialize metrics collector"""
        self.metrics_file = Path(metrics_file)
        self.sessions: Dict[str, SessionMetrics] = {}
        self.load_metrics()
    
    def start_session(self, session_id: str, topic: str) -> SessionMetrics:
        """Start a new session"""
        metrics = SessionMetrics(session_id, topic)
        self.sessions[session_id] = metrics
        logger.info(f"Started tracking metrics for session {session_id}")
        return metrics
    
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get metrics for a session"""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: str, quality_score: int) -> bool:
        """End a session and finalize metrics"""
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return False
        
        metrics = self.sessions[session_id]
        metrics.completed_at = datetime.now()
        metrics.final_quality_score = quality_score
        metrics.calculate_cost()
        
        self.save_session_metrics(metrics)
        logger.info(f"Ended session {session_id}. Duration: {metrics.get_total_duration():.1f}s")
        return True
    
    def save_session_metrics(self, metrics: SessionMetrics):
        """Save session metrics to file"""
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(metrics.to_dict()) + '\n')
            logger.info(f"Saved metrics for session {metrics.session_id}")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def load_metrics(self):
        """Load metrics from file"""
        if not self.metrics_file.exists():
            return
        
        try:
            with open(self.metrics_file, 'r') as f:
                for line in f:
                    if line.strip():
                        # Just load, don't reconstruct sessions
                        json.loads(line)
            logger.info(f"Loaded metrics from {self.metrics_file}")
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
    
    def get_statistics(self) -> dict:
        """Get overall statistics"""
        if not self.sessions:
            return {}
        
        completed = [m for m in self.sessions.values() if m.completed_at]
        if not completed:
            return {}
        
        durations = [m.get_total_duration() for m in completed]
        scores = [m.final_quality_score for m in completed if m.final_quality_score]
        costs = [m.estimated_cost for m in completed]
        
        return {
            'total_sessions': len(self.sessions),
            'completed_sessions': len(completed),
            'average_duration_seconds': sum(durations) / len(durations),
            'min_duration_seconds': min(durations),
            'max_duration_seconds': max(durations),
            'average_quality_score': sum(scores) / len(scores) if scores else 0,
            'total_estimated_cost': sum(costs),
            'average_cost_per_report': sum(costs) / len(costs) if costs else 0,
            'total_api_calls': sum(m.total_api_calls for m in self.sessions.values()),
            'total_tokens': sum(m.total_tokens for m in self.sessions.values())
        }


# Global metrics instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector