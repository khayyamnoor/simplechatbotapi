"""
Flask REST API for the Medical Chatbot.
Provides endpoints for chat functionality and health monitoring.
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization"])

# Global variables
chatbot = None
active_sessions = {}

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
        
        logger.info("Chatbot initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {e}")
        logger.error(traceback.format_exc())
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        model_info = model_loader.get_model_info()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "chatbot_ready": chatbot is not None,
            "model_info": model_info,
            "active_sessions": len(active_sessions)
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/chat/start', methods=['POST'])
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
        active_sessions[session_id] = session
        
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
        
        # Validate message length
        if len(message.strip()) == 0:
            return jsonify({
                "error": "Empty message",
                "message": "Message cannot be empty"
            }), 400
        
        if len(message) > 1000:
            return jsonify({
                "error": "Message too long",
                "message": "Message must be less than 1000 characters"
            }), 400
        
        # Get session
        session = active_sessions.get(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found. Please start a new chat session."
            }), 404
        
        # Process message
        response_data = session.process_message(message.strip())
        
        logger.info(f"Processed message for session {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "response": response_data["response"],
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
def get_chat_history(session_id):
    """Get chat history for a session."""
    try:
        session = active_sessions.get(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found"
            }), 404
        
        history = session.get_conversation_history()
        
        return jsonify({
            "session_id": session_id,
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            "error": "Failed to get chat history",
            "message": str(e)
        }), 500

@app.route('/chat/end/<session_id>', methods=['POST'])
def end_chat(session_id):
    """End a chat session."""
    try:
        session = active_sessions.get(session_id)
        if not session:
            return jsonify({
                "error": "Invalid session",
                "message": "Session not found"
            }), 404
        
        # Clear session data
        session.clear_session()
        
        # Remove from active sessions
        del active_sessions[session_id]
        
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
        
        symptoms = data['symptoms'].strip()
        
        if not symptoms:
            return jsonify({
                "error": "Empty symptoms",
                "message": "Symptoms cannot be empty"
            }), 400
        
        # Get predictions
        predictions = chatbot.predict_disease(symptoms)
        recommendation = chatbot.get_recommendation(predictions, symptoms)
        is_emergency = chatbot.is_emergency(symptoms)
        
        return jsonify({
            "symptoms": symptoms,
            "predictions": predictions,
            "recommendation": recommendation,
            "is_emergency": is_emergency,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in disease prediction: {e}")
        return jsonify({
            "error": "Prediction failed",
            "message": "An error occurred during prediction. Please try again."
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
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        logger.error("Failed to initialize chatbot. Exiting.")
        exit(1)

