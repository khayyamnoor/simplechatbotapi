"""
Secure Flask REST API for the Medical Chatbot with integrated security features.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import uuid
import os
from datetime import datetime
import traceback

from model_loader import model_loader
from chatbot_core import MedicalChatbot, ChatSession
from session_manager import session_manager
from validators import validator
from security import security_manager, require_security_check

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes with security headers
CORS(app, 
     origins="*", 
     methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Limit"])

# Global variables
chatbot = None

def initialize_chatbot():
    """Initialize the chatbot with loaded model and data."""
    global chatbot
    try:
        logger.info("Initializing chatbot...")
        
        # Load model and dataset
        model_loader.load_model()
        model_loader.load_dataset()
        
        # Create chatbot instance
        chatbot = MedicalChatbot(
            model=model_loader.model,
            tokenizer=model_loader.tokenizer,
            device=model_loader.device,
            df=model_loader.df
        )
        
        # Start session cleanup
        session_manager.start_cleanup_thread()
        
        logger.info("Chatbot initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {e}")
        logger.error(traceback.format_exc())
        return False

@app.before_request
def log_request():
    """Log incoming requests for monitoring."""
    client_ip = security_manager.get_client_ip(request)
    logger.info(f"Request from {client_ip}: {request.method} {request.path}")

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Add rate limit headers
    client_ip = security_manager.get_client_ip(request)
    stats = security_manager.rate_limiter.get_client_stats(client_ip)
    
    if 'per_minute' in stats:
        response.headers['X-RateLimit-Limit'] = str(stats['per_minute']['limit'])
        response.headers['X-RateLimit-Remaining'] = str(stats['per_minute']['remaining'])
    
    return response

@app.route('/health', methods=['GET'])
@require_security_check
def health_check():
    """Health check endpoint."""
    try:
        model_info = model_loader.get_model_info()
        security_stats = security_manager.get_security_stats()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "chatbot_ready": chatbot is not None,
            "model_info": model_info,
            "active_sessions": session_manager.get_session_count(),
            "security_stats": security_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/chat/start', methods=['POST'])
@require_security_check
def start_chat():
    """Start a new chat session."""
    try:
        if not chatbot:
            return jsonify({
                "error": "Chatbot not initialized",
                "message": "The chatbot service is not ready. Please try again later."
            }), 503
        
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Create new chat session
        session = ChatSession(session_id, chatbot)
        
        # Store in session manager
        session_manager.create_session(session_id, session)
        
        logger.info(f"Started new chat session: {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "message": "Chat session started successfully",
            "greeting": "Hello! I'm your medical symptom checker. Please describe your symptoms, and I'll try to help. Note: This is not a replacement for professional medical advice."
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting chat session: {e}")
        return jsonify({
            "error": "Failed to start chat session",
            "message": str(e)
        }), 500

@app.route('/chat/message', methods=['POST'])
@require_security_check
def send_message():
    """Send a message to the chatbot."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No data provided",
                "message": "Request body must contain JSON data"
            }), 400
        
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            return jsonify({
                "error": "Missing required fields",
                "message": "Both 'session_id' and 'message' are required"
            }), 400
        
        # Validate session ID
        valid_session, session_error = validator.validate_session_id(session_id)
        if not valid_session:
            return jsonify({
                "error": "Invalid session ID",
                "message": session_error
            }), 400
        
        # Validate message
        valid_message, cleaned_message, message_error = validator.validate_message(message)
        if not valid_message:
            return jsonify({
                "error": "Invalid message",
                "message": message_error
            }), 400
        
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found. Please start a new chat session."
            }), 404
        
        # Process message
        response_data = session.process_message(cleaned_message)
        
        # Update session in manager
        session_manager.update_session(session_id, session)
        
        logger.info(f"Processed message for session {session_id}")
        
        # Sanitize response
        sanitized_response = validator.sanitize_output(response_data["response"])
        
        return jsonify({
            "session_id": session_id,
            "response": sanitized_response,
            "predictions": response_data["predictions"],
            "symptoms": response_data["symptoms"],
            "is_emergency": response_data.get("is_emergency", False),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Failed to process message",
            "message": "An internal error occurred. Please try again."
        }), 500

@app.route('/chat/history/<session_id>', methods=['GET'])
@require_security_check
def get_chat_history(session_id):
    """Get chat history for a session."""
    try:
        # Validate session ID
        valid_session, session_error = validator.validate_session_id(session_id)
        if not valid_session:
            return jsonify({
                "error": "Invalid session ID",
                "message": session_error
            }), 400
        
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found"
            }), 404
        
        history = session.get_conversation_history()
        
        # Sanitize history content
        sanitized_history = []
        for item in history:
            sanitized_item = {
                "role": item["role"],
                "content": validator.sanitize_output(item["content"])
            }
            sanitized_history.append(sanitized_item)
        
        return jsonify({
            "session_id": session_id,
            "history": sanitized_history,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            "error": "Failed to get chat history",
            "message": str(e)
        }), 500

@app.route('/chat/end/<session_id>', methods=['POST'])
@require_security_check
def end_chat(session_id):
    """End a chat session."""
    try:
        # Validate session ID
        valid_session, session_error = validator.validate_session_id(session_id)
        if not valid_session:
            return jsonify({
                "error": "Invalid session ID",
                "message": session_error
            }), 400
        
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found"
            }), 404
        
        # Clear session data
        session.clear_session()
        
        # Remove from session manager
        session_manager.delete_session(session_id)
        
        logger.info(f"Ended chat session: {session_id}")
        
        return jsonify({
            "message": "Chat session ended successfully",
            "session_id": session_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error ending chat session: {e}")
        return jsonify({
            "error": "Failed to end chat session",
            "message": str(e)
        }), 500

@app.route('/predict', methods=['POST'])
@require_security_check
def predict_disease():
    """Direct disease prediction endpoint (stateless)."""
    try:
        if not chatbot:
            return jsonify({
                "error": "Chatbot not initialized",
                "message": "The chatbot service is not ready. Please try again later."
            }), 503
        
        data = request.get_json()
        
        if not data or 'symptoms' not in data:
            return jsonify({
                "error": "Missing symptoms",
                "message": "Request must contain 'symptoms' field"
            }), 400
        
        symptoms = data['symptoms']
        
        # Validate symptoms
        valid_symptoms, cleaned_symptoms, symptoms_error = validator.validate_symptoms(symptoms)
        if not valid_symptoms:
            return jsonify({
                "error": "Invalid symptoms",
                "message": symptoms_error
            }), 400
        
        # Get predictions
        predictions = chatbot.predict_disease(cleaned_symptoms)
        recommendation = chatbot.get_recommendation(predictions, cleaned_symptoms)
        is_emergency = chatbot.is_emergency(cleaned_symptoms)
        
        # Sanitize outputs
        sanitized_recommendation = validator.sanitize_output(recommendation)
        
        return jsonify({
            "symptoms": cleaned_symptoms,
            "predictions": predictions,
            "recommendation": sanitized_recommendation,
            "is_emergency": is_emergency,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in disease prediction: {e}")
        return jsonify({
            "error": "Prediction failed",
            "message": "An error occurred during prediction. Please try again."
        }), 500

@app.route('/admin/stats', methods=['GET'])
@require_security_check
def get_admin_stats():
    """Get administrative statistics (for monitoring)."""
    try:
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "sessions": {
                "active_count": session_manager.get_session_count()
            },
            "security": security_manager.get_security_stats(),
            "model": model_loader.get_model_info()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return jsonify({
            "error": "Failed to get statistics",
            "message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 errors."""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please slow down and try again later."
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    # Initialize chatbot on startup
    if initialize_chatbot():
        logger.info("Starting secure Flask application...")
        try:
            app.run(host='0.0.0.0', port=5000, debug=False)
        finally:
            # Cleanup on shutdown
            session_manager.stop_cleanup_thread()
            logger.info("Application shutdown complete")
    else:
        logger.error("Failed to initialize chatbot. Exiting.")
        exit(1)

