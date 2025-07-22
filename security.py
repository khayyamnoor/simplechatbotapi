"""
Security module for rate limiting and additional protections.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from functools import wraps
from flask import request, jsonify
import hashlib

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        # Store request timestamps for each IP
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Rate limiting rules (requests per time window)
        self.rules = {
            'per_minute': 30,    # 30 requests per minute
            'per_hour': 500,     # 500 requests per hour
            'per_day': 2000      # 2000 requests per day
        }
        
        # Time windows in seconds
        self.windows = {
            'per_minute': 60,
            'per_hour': 3600,
            'per_day': 86400
        }
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, Optional[str]]:
        """Check if request is allowed for the given IP."""
        try:
            current_time = time.time()
            client_requests = self.requests[client_ip]
            
            # Clean old requests and check limits
            for rule_name, limit in self.rules.items():
                window_size = self.windows[rule_name]
                cutoff_time = current_time - window_size
                
                # Remove old requests
                while client_requests and client_requests[0] < cutoff_time:
                    client_requests.popleft()
                
                # Check if limit exceeded
                if len(client_requests) >= limit:
                    return False, f"Rate limit exceeded: {limit} requests per {rule_name.replace('_', ' ')}"
            
            # Add current request
            client_requests.append(current_time)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
            # Allow request if rate limiter fails
            return True, None
    
    def get_client_stats(self, client_ip: str) -> Dict:
        """Get request statistics for a client."""
        try:
            current_time = time.time()
            client_requests = self.requests[client_ip]
            
            stats = {}
            for rule_name, limit in self.rules.items():
                window_size = self.windows[rule_name]
                cutoff_time = current_time - window_size
                
                # Count requests in this window
                count = sum(1 for req_time in client_requests if req_time >= cutoff_time)
                
                stats[rule_name] = {
                    'count': count,
                    'limit': limit,
                    'remaining': max(0, limit - count)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting client stats: {e}")
            return {}

class SecurityManager:
    """Manages security features including rate limiting and request validation."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.blocked_ips = set()
        self.suspicious_requests = defaultdict(int)
        
        # Patterns that might indicate malicious requests
        self.malicious_patterns = [
            'union select',
            'drop table',
            'insert into',
            'delete from',
            'update set',
            '<script',
            'javascript:',
            'eval(',
            'exec(',
            '../',
            '..\\',
            'file://',
            'data:',
            'vbscript:'
        ]
    
    def get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        # Check for forwarded IP first (for proxy/load balancer scenarios)
        if 'X-Forwarded-For' in request.headers:
            return request.headers['X-Forwarded-For'].split(',')[0].strip()
        elif 'X-Real-IP' in request.headers:
            return request.headers['X-Real-IP']
        else:
            return request.remote_addr or 'unknown'
    
    def is_request_allowed(self, request) -> Tuple[bool, Optional[str]]:
        """Check if request should be allowed."""
        try:
            client_ip = self.get_client_ip(request)
            
            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                return False, "IP address is blocked"
            
            # Check rate limiting
            allowed, message = self.rate_limiter.is_allowed(client_ip)
            if not allowed:
                # Increase suspicious activity counter
                self.suspicious_requests[client_ip] += 1
                
                # Block IP if too many rate limit violations
                if self.suspicious_requests[client_ip] > 10:
                    self.blocked_ips.add(client_ip)
                    logger.warning(f"Blocked IP {client_ip} due to excessive rate limit violations")
                
                return False, message
            
            # Check for malicious patterns in request
            if self._contains_malicious_patterns(request):
                self.suspicious_requests[client_ip] += 1
                return False, "Malicious content detected"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking request security: {e}")
            # Allow request if security check fails
            return True, None
    
    def _contains_malicious_patterns(self, request) -> bool:
        """Check if request contains malicious patterns."""
        try:
            # Check URL path
            path = request.path.lower()
            for pattern in self.malicious_patterns:
                if pattern in path:
                    logger.warning(f"Malicious pattern '{pattern}' found in path: {path}")
                    return True
            
            # Check query parameters
            for key, value in request.args.items():
                combined = f"{key}={value}".lower()
                for pattern in self.malicious_patterns:
                    if pattern in combined:
                        logger.warning(f"Malicious pattern '{pattern}' found in query: {combined}")
                        return True
            
            # Check request body if it's JSON
            if request.is_json:
                try:
                    data = request.get_json()
                    if data:
                        data_str = str(data).lower()
                        for pattern in self.malicious_patterns:
                            if pattern in data_str:
                                logger.warning(f"Malicious pattern '{pattern}' found in body")
                                return True
                except:
                    pass  # Ignore JSON parsing errors
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking malicious patterns: {e}")
            return False
    
    def get_security_stats(self) -> Dict:
        """Get security statistics."""
        return {
            'blocked_ips': len(self.blocked_ips),
            'suspicious_requests': dict(self.suspicious_requests),
            'total_suspicious_ips': len(self.suspicious_requests)
        }

# Global security manager
security_manager = SecurityManager()

def require_security_check(f):
    """Decorator to add security checks to Flask routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Check if request is allowed
            allowed, message = security_manager.is_request_allowed(request)
            
            if not allowed:
                logger.warning(f"Blocked request from {security_manager.get_client_ip(request)}: {message}")
                return jsonify({
                    "error": "Request blocked",
                    "message": "Your request has been blocked due to security policies"
                }), 429  # Too Many Requests
            
            # Add security headers to response
            response = f(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response
            
        except Exception as e:
            logger.error(f"Error in security check: {e}")
            # Continue with request if security check fails
            return f(*args, **kwargs)
    
    return decorated_function

def get_request_hash(request) -> str:
    """Generate a hash for request deduplication."""
    try:
        # Create hash based on IP, path, and body
        client_ip = security_manager.get_client_ip(request)
        path = request.path
        
        # Include request body if present
        body = ""
        if request.is_json:
            try:
                body = str(request.get_json())
            except:
                pass
        
        hash_input = f"{client_ip}:{path}:{body}"
        return hashlib.md5(hash_input.encode()).hexdigest()
        
    except Exception as e:
        logger.error(f"Error generating request hash: {e}")
        return "unknown"

