# Medical Chatbot REST API

A production-ready REST API for a medical symptom checker chatbot, designed for integration with Laravel PHP backends and JavaScript frontends.

## Features

- **Fixed Core Logic**: Resolved critical bugs from the original notebook code
- **REST API**: Full Flask-based REST API with proper error handling
- **Session Management**: Stateful chat sessions with automatic cleanup
- **Security**: Rate limiting, input validation, CORS support, and malicious content detection
- **Production Ready**: Comprehensive logging, monitoring, and error handling

## API Endpoints

### Health Check
```
GET /health
```
Returns API health status and system information.

### Chat Session Management

#### Start Chat Session
```
POST /chat/start
```
Creates a new chat session and returns a session ID.

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "Chat session started successfully",
  "greeting": "Hello! I'm your medical symptom checker..."
}
```

#### Send Message
```
POST /chat/message
```
Send a message to the chatbot within a session.

**Request:**
```json
{
  "session_id": "uuid-string",
  "message": "I have fever and cough"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "response": "Based on your symptoms...",
  "predictions": [
    {
      "disease": "flu",
      "confidence": 0.8,
      "source": "dataset"
    }
  ],
  "symptoms": "fever, cough",
  "is_emergency": false,
  "timestamp": "2025-07-21T23:06:10.032960"
}
```

#### Get Chat History
```
GET /chat/history/<session_id>
```
Retrieve conversation history for a session.

#### End Chat Session
```
POST /chat/end/<session_id>
```
End a chat session and clean up resources.

### Direct Prediction

#### Predict Disease
```
POST /predict
```
Get disease predictions without maintaining session state.

**Request:**
```json
{
  "symptoms": "headache, nausea, vomiting"
}
```

**Response:**
```json
{
  "symptoms": "headache, nausea, vomiting",
  "predictions": [...],
  "recommendation": "Your symptoms might suggest...",
  "is_emergency": false,
  "timestamp": "2025-07-21T23:06:20.749074"
}
```

## Installation and Setup

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the API:**
```bash
python app_secure.py
```

The API will start on `http://0.0.0.0:5000`

## Security Features

- **Rate Limiting**: 30 requests/minute, 500/hour, 2000/day per IP
- **Input Validation**: Sanitizes and validates all user inputs
- **Malicious Content Detection**: Blocks XSS, SQL injection attempts
- **CORS Support**: Configured for cross-origin requests
- **Security Headers**: Adds security headers to all responses

## Error Handling

The API returns consistent error responses:

```json
{
  "error": "Error type",
  "message": "Human-readable error message"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `404`: Not Found (invalid session)
- `429`: Too Many Requests (rate limited)
- `500`: Internal Server Error
- `503`: Service Unavailable (chatbot not ready)

## Architecture

- **Model Loader**: Handles ML model and dataset loading
- **Chatbot Core**: Fixed core logic with improved prediction algorithms
- **Session Manager**: Manages chat sessions with automatic cleanup
- **Validators**: Input validation and sanitization
- **Security**: Rate limiting and malicious content detection
- **Flask App**: Main API application with comprehensive error handling

## Files Structure

```
chatbot_api/
├── app_secure.py          # Main Flask application
├── model_loader.py        # Model and dataset loading
├── chatbot_core.py        # Fixed chatbot logic
├── session_manager.py     # Session management
├── validators.py          # Input validation
├── security.py           # Security features
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Integration Notes

- The API is designed to work with any frontend framework
- CORS is enabled for all origins
- All responses are JSON formatted
- Session IDs are UUIDs for security
- Input validation prevents common attacks
- Rate limiting protects against abuse

