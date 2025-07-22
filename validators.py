"""
Input validation and sanitization module.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class InputValidator:
    """Handles input validation and sanitization."""
    
    def __init__(self):
        # Define allowed characters for symptoms (letters, numbers, spaces, common punctuation)
        self.symptom_pattern = re.compile(r'^[a-zA-Z0-9\s,.\-()]+$')
        
        # Common medical terms that should be allowed
        self.medical_terms = {
            'pain', 'ache', 'fever', 'cough', 'nausea', 'vomiting', 'headache',
            'dizziness', 'fatigue', 'weakness', 'shortness', 'breathing',
            'chest', 'abdominal', 'stomach', 'throat', 'runny', 'nose',
            'congestion', 'sneezing', 'itching', 'rash', 'swelling',
            'muscle', 'joint', 'back', 'neck', 'leg', 'arm', 'hand', 'foot'
        }
        
        # Suspicious patterns that might indicate injection attempts
        self.suspicious_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'import\s+',
            r'from\s+\w+\s+import',
            r'__\w+__',
            r'\.\./',
            r'file://',
            r'http[s]?://'
        ]
    
    def validate_symptoms(self, symptoms: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate symptom input.
        
        Returns:
            Tuple of (is_valid, cleaned_symptoms, error_message)
        """
        try:
            if not symptoms or not isinstance(symptoms, str):
                return False, "", "Symptoms must be a non-empty string"
            
            # Basic length check
            if len(symptoms.strip()) == 0:
                return False, "", "Symptoms cannot be empty"
            
            if len(symptoms) > 1000:
                return False, "", "Symptoms description is too long (max 1000 characters)"
            
            # Check for suspicious patterns
            for pattern in self.suspicious_patterns:
                if re.search(pattern, symptoms, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected in symptoms: {pattern}")
                    return False, "", "Invalid characters detected in symptoms"
            
            # Clean and normalize the input
            cleaned = self._clean_symptoms(symptoms)
            
            if not cleaned:
                return False, "", "No valid symptoms found after cleaning"
            
            # Validate cleaned symptoms
            if not self.symptom_pattern.match(cleaned):
                return False, "", "Symptoms contain invalid characters"
            
            return True, cleaned, None
            
        except Exception as e:
            logger.error(f"Error validating symptoms: {e}")
            return False, "", "Validation error occurred"
    
    def validate_session_id(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate session ID format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not session_id or not isinstance(session_id, str):
                return False, "Session ID must be a non-empty string"
            
            # Check length
            if len(session_id) < 10 or len(session_id) > 100:
                return False, "Invalid session ID format"
            
            # Check for valid UUID-like format (alphanumeric and hyphens)
            if not re.match(r'^[a-zA-Z0-9\-]+$', session_id):
                return False, "Session ID contains invalid characters"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating session ID: {e}")
            return False, "Session ID validation error"
    
    def validate_message(self, message: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate chat message.
        
        Returns:
            Tuple of (is_valid, cleaned_message, error_message)
        """
        try:
            if not message or not isinstance(message, str):
                return False, "", "Message must be a non-empty string"
            
            # Basic length check
            if len(message.strip()) == 0:
                return False, "", "Message cannot be empty"
            
            if len(message) > 2000:
                return False, "", "Message is too long (max 2000 characters)"
            
            # Check for suspicious patterns
            for pattern in self.suspicious_patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected in message: {pattern}")
                    return False, "", "Invalid content detected in message"
            
            # Clean the message
            cleaned = self._clean_message(message)
            
            if not cleaned:
                return False, "", "No valid content found after cleaning"
            
            return True, cleaned, None
            
        except Exception as e:
            logger.error(f"Error validating message: {e}")
            return False, "", "Message validation error"
    
    def _clean_symptoms(self, symptoms: str) -> str:
        """Clean and normalize symptom input."""
        # Remove extra whitespace
        cleaned = ' '.join(symptoms.split())
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # Normalize common separators
        cleaned = re.sub(r'[;|]+', ',', cleaned)
        
        # Remove multiple consecutive commas
        cleaned = re.sub(r',+', ',', cleaned)
        
        # Remove leading/trailing commas
        cleaned = cleaned.strip(',')
        
        return cleaned
    
    def _clean_message(self, message: str) -> str:
        """Clean and normalize message input."""
        # Remove extra whitespace
        cleaned = ' '.join(message.split())
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def sanitize_output(self, text: str) -> str:
        """Sanitize output text to prevent XSS."""
        if not text:
            return ""
        
        # Basic HTML entity encoding for common characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text

# Global validator instance
validator = InputValidator()

