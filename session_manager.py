"""
Session management module for handling user sessions and cleanup.
"""

import time
import threading
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages chat sessions with automatic cleanup."""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, dict] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.cleanup_thread = None
        self.running = False
        
    def start_cleanup_thread(self):
        """Start the background cleanup thread."""
        if not self.running:
            self.running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
            self.cleanup_thread.start()
            logger.info("Session cleanup thread started")
    
    def stop_cleanup_thread(self):
        """Stop the background cleanup thread."""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
            logger.info("Session cleanup thread stopped")
    
    def create_session(self, session_id: str, session_data: dict) -> bool:
        """Create a new session."""
        try:
            self.sessions[session_id] = {
                'data': session_data,
                'created_at': datetime.utcnow(),
                'last_accessed': datetime.utcnow()
            }
            logger.info(f"Created session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data and update last accessed time."""
        if session_id in self.sessions:
            self.sessions[session_id]['last_accessed'] = datetime.utcnow()
            return self.sessions[session_id]['data']
        return None
    
    def update_session(self, session_id: str, session_data: dict) -> bool:
        """Update session data."""
        if session_id in self.sessions:
            self.sessions[session_id]['data'] = session_data
            self.sessions[session_id]['last_accessed'] = datetime.utcnow()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session metadata."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                'session_id': session_id,
                'created_at': session['created_at'].isoformat(),
                'last_accessed': session['last_accessed'].isoformat(),
                'age_minutes': (datetime.utcnow() - session['created_at']).total_seconds() / 60
            }
        return None
    
    def _cleanup_expired_sessions(self):
        """Background thread to clean up expired sessions."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                expired_sessions = []
                
                for session_id, session_info in self.sessions.items():
                    if current_time - session_info['last_accessed'] > self.session_timeout:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    self.delete_session(session_id)
                    logger.info(f"Cleaned up expired session: {session_id}")
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Sleep for 5 minutes before next cleanup
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

# Global session manager instance
session_manager = SessionManager()

