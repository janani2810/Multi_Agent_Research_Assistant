"""Session management and caching for the research system"""

import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import logging

logger = logging.getLogger(__name__)


class SessionCache:
    """In-memory cache with optional persistence"""
    
    def __init__(self, cache_dir: str = ".cache", ttl_minutes: int = 60):
        """Initialize session cache"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _get_cache_key(self, topic: str) -> str:
        """Generate cache key from topic"""
        return hashlib.md5(topic.lower().encode()).hexdigest()
    
    def get(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get cached research results"""
        key = self._get_cache_key(topic)
        
        # Check memory cache first
        if key in self.memory_cache:
            cached = self.memory_cache[key]
            if datetime.now() - cached['timestamp'] < self.ttl:
                logger.info(f"Cache hit for topic: {topic}")
                return cached['data']
            else:
                del self.memory_cache[key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                if datetime.now() - cached['timestamp'] < self.ttl:
                    self.memory_cache[key] = cached
                    logger.info(f"Disk cache hit for topic: {topic}")
                    return cached['data']
                else:
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
        
        return None
    
    def set(self, topic: str, data: Dict[str, Any], persist: bool = True):
        """Cache research results"""
        key = self._get_cache_key(topic)
        cached = {
            'timestamp': datetime.now(),
            'data': data
        }
        
        # Store in memory
        self.memory_cache[key] = cached
        
        # Optionally persist to disk
        if persist:
            try:
                cache_file = self.cache_dir / f"{key}.pkl"
                with open(cache_file, 'wb') as f:
                    pickle.dump(cached, f)
                logger.info(f"Cached results for topic: {topic}")
            except Exception as e:
                logger.error(f"Error saving cache: {e}")
    
    def clear(self, topic: Optional[str] = None):
        """Clear cache"""
        if topic:
            key = self._get_cache_key(topic)
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
        else:
            self.memory_cache.clear()
            for f in self.cache_dir.glob("*.pkl"):
                f.unlink()
        
        logger.info(f"Cache cleared for topic: {topic or 'all'}")


class SessionManager:
    """Manages research sessions with persistence"""
    
    def __init__(self, sessions_dir: str = ".sessions"):
        """Initialize session manager"""
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.cache = SessionCache()
    
    def create_session(self, session_id: str, topic: str) -> Dict[str, Any]:
        """Create a new session"""
        session = {
            'session_id': session_id,
            'topic': topic,
            'created_at': datetime.now().isoformat(),
            'status': 'initializing',
            'data': {}
        }
        self.sessions[session_id] = session
        self._save_session(session)
        logger.info(f"Created session {session_id}")
        return session
    
    def update_session(self, session_id: str, **kwargs):
        """Update session data"""
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return
        
        self.sessions[session_id].update(kwargs)
        self._save_session(self.sessions[session_id])
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try to load from disk
        return self._load_session(session_id)
    
    def _save_session(self, session: Dict[str, Any]):
        """Save session to disk"""
        try:
            session_file = self.sessions_dir / f"{session['session_id']}.json"
            with open(session_file, 'w') as f:
                json.dump(session, f, default=str)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from disk"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session = json.load(f)
                self.sessions[session_id] = session
                return session
        except Exception as e:
            logger.error(f"Error loading session: {e}")
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
    
    def list_sessions(self, limit: int = 10) -> list:
        """List recent sessions"""
        sessions = list(self.sessions.values())
        return sorted(
            sessions,
            key=lambda x: x['created_at'],
            reverse=True
        )[:limit]
    
    def cleanup_old_sessions(self, days: int = 7):
        """Remove sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        to_delete = []
        
        for session_id, session in self.sessions.items():
            created = datetime.fromisoformat(session['created_at'])
            if created < cutoff_date:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        logger.info(f"Cleaned up {len(to_delete)} old sessions")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager