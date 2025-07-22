# JavaScript Frontend Integration Guide

This guide shows how to integrate the Medical Chatbot API with JavaScript frontends (vanilla JS, React, Vue, etc.).

## JavaScript API Client Class

Create a reusable API client class:

```javascript
class ChatbotAPI {
    constructor(baseUrl = 'http://localhost:5000', timeout = 30000) {
        this.baseUrl = baseUrl;
        this.timeout = timeout;
        this.currentSessionId = null;
    }

    /**
     * Make HTTP request with error handling
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    /**
     * Check API health
     */
    async healthCheck() {
        return await this.makeRequest('/health');
    }

    /**
     * Start a new chat session
     */
    async startChatSession() {
        const result = await this.makeRequest('/chat/start', {
            method: 'POST'
        });
        
        if (result.session_id) {
            this.currentSessionId = result.session_id;
        }
        
        return result;
    }

    /**
     * Send a message to the chatbot
     */
    async sendMessage(message, sessionId = null) {
        const targetSessionId = sessionId || this.currentSessionId;
        
        if (!targetSessionId) {
            throw new Error('No active session. Please start a chat session first.');
        }

        return await this.makeRequest('/chat/message', {
            method: 'POST',
            body: JSON.stringify({
                session_id: targetSessionId,
                message: message
            })
        });
    }

    /**
     * Get chat history
     */
    async getChatHistory(sessionId = null) {
        const targetSessionId = sessionId || this.currentSessionId;
        
        if (!targetSessionId) {
            throw new Error('No active session.');
        }

        return await this.makeRequest(`/chat/history/${targetSessionId}`);
    }

    /**
     * End chat session
     */
    async endChatSession(sessionId = null) {
        const targetSessionId = sessionId || this.currentSessionId;
        
        if (!targetSessionId) {
            throw new Error('No active session.');
        }

        const result = await this.makeRequest(`/chat/end/${targetSessionId}`, {
            method: 'POST'
        });

        if (targetSessionId === this.currentSessionId) {
            this.currentSessionId = null;
        }

        return result;
    }

    /**
     * Get direct disease prediction
     */
    async predictDisease(symptoms) {
        return await this.makeRequest('/predict', {
            method: 'POST',
            body: JSON.stringify({
                symptoms: symptoms
            })
        });
    }

    /**
     * Get current session ID
     */
    getCurrentSessionId() {
        return this.currentSessionId;
    }

    /**
     * Set session ID (for resuming sessions)
     */
    setCurrentSessionId(sessionId) {
        this.currentSessionId = sessionId;
    }
}
```

## Vanilla JavaScript Example

Complete chat interface implementation:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medical Chatbot</title>
    <style>
        .chat-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            font-family: Arial, sans-serif;
        }
        
        .chat-messages {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
        }
        
        .message {
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 5px;
        }
        
        .user-message {
            background-color: #007bff;
            color: white;
            text-align: right;
        }
        
        .bot-message {
            background-color: #e9ecef;
            color: #333;
        }
        
        .emergency {
            background-color: #dc3545;
            color: white;
            font-weight: bold;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
        }
        
        .message-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        .send-button {
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .send-button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        
        .status {
            margin-bottom: 10px;
            padding: 5px;
            text-align: center;
            font-size: 14px;
        }
        
        .status.connected {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>Medical Symptom Checker</h1>
        <div id="status" class="status">Connecting...</div>
        <div id="chatMessages" class="chat-messages"></div>
        <div class="input-container">
            <input 
                type="text" 
                id="messageInput" 
                class="message-input" 
                placeholder="Describe your symptoms..."
                disabled
            >
            <button id="sendButton" class="send-button" disabled>Send</button>
            <button id="endButton" class="send-button" disabled>End Chat</button>
        </div>
    </div>

    <script>
        // Include the ChatbotAPI class here or import it
        // ... (ChatbotAPI class code from above)

        class ChatInterface {
            constructor() {
                this.api = new ChatbotAPI();
                this.messagesContainer = document.getElementById('chatMessages');
                this.messageInput = document.getElementById('messageInput');
                this.sendButton = document.getElementById('sendButton');
                this.endButton = document.getElementById('endButton');
                this.statusDiv = document.getElementById('status');
                
                this.init();
            }

            async init() {
                try {
                    // Check API health
                    await this.api.healthCheck();
                    this.updateStatus('Connected', 'connected');
                    
                    // Start chat session
                    const session = await this.api.startChatSession();
                    this.addMessage('bot', session.greeting);
                    
                    // Enable interface
                    this.messageInput.disabled = false;
                    this.sendButton.disabled = false;
                    this.endButton.disabled = false;
                    
                    // Add event listeners
                    this.setupEventListeners();
                    
                } catch (error) {
                    this.updateStatus(`Error: ${error.message}`, 'error');
                }
            }

            setupEventListeners() {
                this.sendButton.addEventListener('click', () => this.sendMessage());
                this.endButton.addEventListener('click', () => this.endChat());
                
                this.messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                });
            }

            async sendMessage() {
                const message = this.messageInput.value.trim();
                if (!message) return;

                // Disable input while processing
                this.messageInput.disabled = true;
                this.sendButton.disabled = true;

                try {
                    // Add user message to chat
                    this.addMessage('user', message);
                    this.messageInput.value = '';

                    // Send to API
                    const response = await this.api.sendMessage(message);
                    
                    // Add bot response
                    this.addMessage('bot', response.response, response.is_emergency);
                    
                    // Show predictions if available
                    if (response.predictions && response.predictions.length > 0) {
                        this.showPredictions(response.predictions);
                    }

                } catch (error) {
                    this.addMessage('bot', `Error: ${error.message}`, false, true);
                } finally {
                    // Re-enable input
                    this.messageInput.disabled = false;
                    this.sendButton.disabled = false;
                    this.messageInput.focus();
                }
            }

            async endChat() {
                try {
                    await this.api.endChatSession();
                    this.addMessage('bot', 'Chat session ended. Thank you for using the medical symptom checker.');
                    
                    // Disable interface
                    this.messageInput.disabled = true;
                    this.sendButton.disabled = true;
                    this.endButton.disabled = true;
                    
                    this.updateStatus('Chat ended', 'connected');
                    
                } catch (error) {
                    this.updateStatus(`Error ending chat: ${error.message}`, 'error');
                }
            }

            addMessage(sender, content, isEmergency = false, isError = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                
                if (isEmergency) {
                    messageDiv.classList.add('emergency');
                }
                
                if (isError) {
                    messageDiv.style.backgroundColor = '#f8d7da';
                    messageDiv.style.color = '#721c24';
                }
                
                messageDiv.textContent = content;
                this.messagesContainer.appendChild(messageDiv);
                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            }

            showPredictions(predictions) {
                const predictionText = predictions
                    .slice(0, 3) // Show top 3 predictions
                    .map((pred, index) => 
                        `${index + 1}. ${pred.disease} (${Math.round(pred.confidence * 100)}% confidence)`
                    )
                    .join('\n');
                
                this.addMessage('bot', `Top predictions:\n${predictionText}`);
            }

            updateStatus(message, type) {
                this.statusDiv.textContent = message;
                this.statusDiv.className = `status ${type}`;
            }
        }

        // Initialize chat interface when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new ChatInterface();
        });
    </script>
</body>
</html>
```

## React Component Example

```jsx
import React, { useState, useEffect, useRef } from 'react';

const ChatbotComponent = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const messagesEndRef = useRef(null);
    const api = useRef(new ChatbotAPI());

    useEffect(() => {
        initializeChat();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const initializeChat = async () => {
        try {
            setIsLoading(true);
            
            // Check API health
            await api.current.healthCheck();
            
            // Start chat session
            const session = await api.current.startChatSession();
            setSessionId(session.session_id);
            setIsConnected(true);
            
            // Add greeting message
            setMessages([{
                id: Date.now(),
                sender: 'bot',
                content: session.greeting,
                timestamp: new Date()
            }]);
            
        } catch (error) {
            console.error('Failed to initialize chat:', error);
            setMessages([{
                id: Date.now(),
                sender: 'bot',
                content: `Error: ${error.message}`,
                timestamp: new Date(),
                isError: true
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const sendMessage = async () => {
        if (!inputMessage.trim() || isLoading || !sessionId) return;

        const userMessage = {
            id: Date.now(),
            sender: 'user',
            content: inputMessage,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
            const response = await api.current.sendMessage(inputMessage);
            
            const botMessage = {
                id: Date.now() + 1,
                sender: 'bot',
                content: response.response,
                timestamp: new Date(),
                isEmergency: response.is_emergency,
                predictions: response.predictions
            };

            setMessages(prev => [...prev, botMessage]);

        } catch (error) {
            const errorMessage = {
                id: Date.now() + 1,
                sender: 'bot',
                content: `Error: ${error.message}`,
                timestamp: new Date(),
                isError: true
            };

            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const endChat = async () => {
        if (!sessionId) return;

        try {
            await api.current.endChatSession();
            setIsConnected(false);
            setSessionId(null);
            
            setMessages(prev => [...prev, {
                id: Date.now(),
                sender: 'bot',
                content: 'Chat session ended. Thank you!',
                timestamp: new Date()
            }]);
            
        } catch (error) {
            console.error('Failed to end chat:', error);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="chatbot-container">
            <div className="chat-header">
                <h2>Medical Symptom Checker</h2>
                <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                </div>
            </div>
            
            <div className="chat-messages">
                {messages.map(message => (
                    <div 
                        key={message.id} 
                        className={`message ${message.sender}-message ${
                            message.isEmergency ? 'emergency' : ''
                        } ${message.isError ? 'error' : ''}`}
                    >
                        <div className="message-content">{message.content}</div>
                        {message.predictions && (
                            <div className="predictions">
                                <strong>Top predictions:</strong>
                                <ul>
                                    {message.predictions.slice(0, 3).map((pred, index) => (
                                        <li key={index}>
                                            {pred.disease} ({Math.round(pred.confidence * 100)}%)
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        <div className="message-time">
                            {message.timestamp.toLocaleTimeString()}
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="message bot-message loading">
                        <div className="typing-indicator">Bot is typing...</div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            
            <div className="chat-input">
                <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Describe your symptoms..."
                    disabled={!isConnected || isLoading}
                    className="message-input"
                />
                <button 
                    onClick={sendMessage}
                    disabled={!isConnected || isLoading || !inputMessage.trim()}
                    className="send-button"
                >
                    Send
                </button>
                <button 
                    onClick={endChat}
                    disabled={!isConnected}
                    className="end-button"
                >
                    End Chat
                </button>
            </div>
        </div>
    );
};

export default ChatbotComponent;
```

## Vue.js Component Example

```vue
<template>
  <div class="chatbot-container">
    <div class="chat-header">
      <h2>Medical Symptom Checker</h2>
      <div :class="['status', isConnected ? 'connected' : 'disconnected']">
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </div>
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="message in messages" 
        :key="message.id"
        :class="[
          'message', 
          `${message.sender}-message`,
          { 'emergency': message.isEmergency },
          { 'error': message.isError }
        ]"
      >
        <div class="message-content">{{ message.content }}</div>
        <div v-if="message.predictions" class="predictions">
          <strong>Top predictions:</strong>
          <ul>
            <li v-for="(pred, index) in message.predictions.slice(0, 3)" :key="index">
              {{ pred.disease }} ({{ Math.round(pred.confidence * 100) }}%)
            </li>
          </ul>
        </div>
        <div class="message-time">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
      
      <div v-if="isLoading" class="message bot-message loading">
        <div class="typing-indicator">Bot is typing...</div>
      </div>
    </div>
    
    <div class="chat-input">
      <input
        v-model="inputMessage"
        @keypress="handleKeyPress"
        :disabled="!isConnected || isLoading"
        placeholder="Describe your symptoms..."
        class="message-input"
      />
      <button 
        @click="sendMessage"
        :disabled="!isConnected || isLoading || !inputMessage.trim()"
        class="send-button"
      >
        Send
      </button>
      <button 
        @click="endChat"
        :disabled="!isConnected"
        class="end-button"
      >
        End Chat
      </button>
    </div>
  </div>
</template>

<script>
import { ChatbotAPI } from './chatbot-api.js';

export default {
  name: 'ChatbotComponent',
  data() {
    return {
      messages: [],
      inputMessage: '',
      isLoading: false,
      sessionId: null,
      isConnected: false,
      api: new ChatbotAPI()
    };
  },
  
  async mounted() {
    await this.initializeChat();
  },
  
  methods: {
    async initializeChat() {
      try {
        this.isLoading = true;
        
        // Check API health
        await this.api.healthCheck();
        
        // Start chat session
        const session = await this.api.startChatSession();
        this.sessionId = session.session_id;
        this.isConnected = true;
        
        // Add greeting message
        this.addMessage('bot', session.greeting);
        
      } catch (error) {
        console.error('Failed to initialize chat:', error);
        this.addMessage('bot', `Error: ${error.message}`, false, true);
      } finally {
        this.isLoading = false;
      }
    },
    
    async sendMessage() {
      if (!this.inputMessage.trim() || this.isLoading || !this.sessionId) return;

      const message = this.inputMessage;
      this.addMessage('user', message);
      this.inputMessage = '';
      this.isLoading = true;

      try {
        const response = await this.api.sendMessage(message);
        this.addMessage('bot', response.response, response.is_emergency, false, response.predictions);
      } catch (error) {
        this.addMessage('bot', `Error: ${error.message}`, false, true);
      } finally {
        this.isLoading = false;
      }
    },
    
    async endChat() {
      if (!this.sessionId) return;

      try {
        await this.api.endChatSession();
        this.isConnected = false;
        this.sessionId = null;
        this.addMessage('bot', 'Chat session ended. Thank you!');
      } catch (error) {
        console.error('Failed to end chat:', error);
      }
    },
    
    addMessage(sender, content, isEmergency = false, isError = false, predictions = null) {
      const message = {
        id: Date.now() + Math.random(),
        sender,
        content,
        timestamp: new Date(),
        isEmergency,
        isError,
        predictions
      };
      
      this.messages.push(message);
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      container.scrollTop = container.scrollHeight;
    },
    
    handleKeyPress(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    },
    
    formatTime(timestamp) {
      return timestamp.toLocaleTimeString();
    }
  }
};
</script>
```

## Error Handling Best Practices

```javascript
// Comprehensive error handling wrapper
class ChatbotAPIWithRetry extends ChatbotAPI {
    constructor(baseUrl, timeout, maxRetries = 3) {
        super(baseUrl, timeout);
        this.maxRetries = maxRetries;
    }

    async makeRequestWithRetry(endpoint, options = {}, retryCount = 0) {
        try {
            return await this.makeRequest(endpoint, options);
        } catch (error) {
            if (retryCount < this.maxRetries && this.shouldRetry(error)) {
                console.warn(`Request failed, retrying (${retryCount + 1}/${this.maxRetries}):`, error.message);
                await this.delay(1000 * (retryCount + 1)); // Exponential backoff
                return await this.makeRequestWithRetry(endpoint, options, retryCount + 1);
            }
            throw error;
        }
    }

    shouldRetry(error) {
        // Retry on network errors, timeouts, and 5xx server errors
        return error.message.includes('timeout') || 
               error.message.includes('network') ||
               error.message.includes('500') ||
               error.message.includes('502') ||
               error.message.includes('503');
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
```

This comprehensive integration guide provides everything needed to connect your JavaScript frontend with the medical chatbot API, including error handling, retry logic, and complete UI examples.

