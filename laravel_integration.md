# Laravel PHP Backend Integration Guide

This guide shows how to integrate the Medical Chatbot API with a Laravel PHP backend.

## Laravel Service Class

Create a service class to handle API communication:

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Exception;

class ChatbotService
{
    private $apiBaseUrl;
    private $timeout;

    public function __construct()
    {
        $this->apiBaseUrl = config('chatbot.api_url', 'http://localhost:5000');
        $this->timeout = config('chatbot.timeout', 30);
    }

    /**
     * Check if the chatbot API is healthy
     */
    public function healthCheck()
    {
        try {
            $response = Http::timeout($this->timeout)
                ->get($this->apiBaseUrl . '/health');

            if ($response->successful()) {
                return $response->json();
            }

            return ['status' => 'unhealthy', 'error' => 'API not responding'];
        } catch (Exception $e) {
            Log::error('Chatbot health check failed: ' . $e->getMessage());
            return ['status' => 'error', 'message' => $e->getMessage()];
        }
    }

    /**
     * Start a new chat session
     */
    public function startChatSession()
    {
        try {
            $response = Http::timeout($this->timeout)
                ->post($this->apiBaseUrl . '/chat/start');

            if ($response->successful()) {
                return $response->json();
            }

            return ['error' => 'Failed to start chat session'];
        } catch (Exception $e) {
            Log::error('Failed to start chat session: ' . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * Send a message to the chatbot
     */
    public function sendMessage($sessionId, $message)
    {
        try {
            $response = Http::timeout($this->timeout)
                ->post($this->apiBaseUrl . '/chat/message', [
                    'session_id' => $sessionId,
                    'message' => $message
                ]);

            if ($response->successful()) {
                return $response->json();
            }

            $errorData = $response->json();
            return ['error' => $errorData['message'] ?? 'Failed to send message'];
        } catch (Exception $e) {
            Log::error('Failed to send message: ' . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * Get chat history
     */
    public function getChatHistory($sessionId)
    {
        try {
            $response = Http::timeout($this->timeout)
                ->get($this->apiBaseUrl . '/chat/history/' . $sessionId);

            if ($response->successful()) {
                return $response->json();
            }

            return ['error' => 'Failed to get chat history'];
        } catch (Exception $e) {
            Log::error('Failed to get chat history: ' . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * End a chat session
     */
    public function endChatSession($sessionId)
    {
        try {
            $response = Http::timeout($this->timeout)
                ->post($this->apiBaseUrl . '/chat/end/' . $sessionId);

            if ($response->successful()) {
                return $response->json();
            }

            return ['error' => 'Failed to end chat session'];
        } catch (Exception $e) {
            Log::error('Failed to end chat session: ' . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * Get direct disease prediction
     */
    public function predictDisease($symptoms)
    {
        try {
            $response = Http::timeout($this->timeout)
                ->post($this->apiBaseUrl . '/predict', [
                    'symptoms' => $symptoms
                ]);

            if ($response->successful()) {
                return $response->json();
            }

            $errorData = $response->json();
            return ['error' => $errorData['message'] ?? 'Prediction failed'];
        } catch (Exception $e) {
            Log::error('Disease prediction failed: ' . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }
}
```

## Laravel Controller

Create a controller to handle chatbot requests:

```php
<?php

namespace App\Http\Controllers;

use App\Services\ChatbotService;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Validator;

class ChatbotController extends Controller
{
    private $chatbotService;

    public function __construct(ChatbotService $chatbotService)
    {
        $this->chatbotService = $chatbotService;
    }

    /**
     * Start a new chat session
     */
    public function startChat(): JsonResponse
    {
        $result = $this->chatbotService->startChatSession();
        
        if (isset($result['error'])) {
            return response()->json($result, 500);
        }

        return response()->json($result);
    }

    /**
     * Send a message to the chatbot
     */
    public function sendMessage(Request $request): JsonResponse
    {
        $validator = Validator::make($request->all(), [
            'session_id' => 'required|string',
            'message' => 'required|string|max:1000'
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'messages' => $validator->errors()
            ], 400);
        }

        $result = $this->chatbotService->sendMessage(
            $request->session_id,
            $request->message
        );

        if (isset($result['error'])) {
            return response()->json($result, 500);
        }

        return response()->json($result);
    }

    /**
     * Get chat history
     */
    public function getChatHistory($sessionId): JsonResponse
    {
        if (empty($sessionId)) {
            return response()->json(['error' => 'Session ID is required'], 400);
        }

        $result = $this->chatbotService->getChatHistory($sessionId);

        if (isset($result['error'])) {
            return response()->json($result, 404);
        }

        return response()->json($result);
    }

    /**
     * End chat session
     */
    public function endChat($sessionId): JsonResponse
    {
        if (empty($sessionId)) {
            return response()->json(['error' => 'Session ID is required'], 400);
        }

        $result = $this->chatbotService->endChatSession($sessionId);

        if (isset($result['error'])) {
            return response()->json($result, 500);
        }

        return response()->json($result);
    }

    /**
     * Get direct disease prediction
     */
    public function predictDisease(Request $request): JsonResponse
    {
        $validator = Validator::make($request->all(), [
            'symptoms' => 'required|string|max:1000'
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'messages' => $validator->errors()
            ], 400);
        }

        $result = $this->chatbotService->predictDisease($request->symptoms);

        if (isset($result['error'])) {
            return response()->json($result, 500);
        }

        return response()->json($result);
    }

    /**
     * Health check
     */
    public function healthCheck(): JsonResponse
    {
        $result = $this->chatbotService->healthCheck();
        return response()->json($result);
    }
}
```

## Laravel Routes

Add these routes to your `routes/api.php`:

```php
<?php

use App\Http\Controllers\ChatbotController;
use Illuminate\Support\Facades\Route;

Route::prefix('chatbot')->group(function () {
    Route::get('/health', [ChatbotController::class, 'healthCheck']);
    Route::post('/chat/start', [ChatbotController::class, 'startChat']);
    Route::post('/chat/message', [ChatbotController::class, 'sendMessage']);
    Route::get('/chat/history/{sessionId}', [ChatbotController::class, 'getChatHistory']);
    Route::post('/chat/end/{sessionId}', [ChatbotController::class, 'endChat']);
    Route::post('/predict', [ChatbotController::class, 'predictDisease']);
});
```

## Configuration

Add chatbot configuration to `config/chatbot.php`:

```php
<?php

return [
    'api_url' => env('CHATBOT_API_URL', 'http://localhost:5000'),
    'timeout' => env('CHATBOT_API_TIMEOUT', 30),
];
```

Add to your `.env` file:

```env
CHATBOT_API_URL=http://localhost:5000
CHATBOT_API_TIMEOUT=30
```

## Database Migration (Optional)

If you want to store chat sessions in your database:

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateChatSessionsTable extends Migration
{
    public function up()
    {
        Schema::create('chat_sessions', function (Blueprint $table) {
            $table->id();
            $table->string('session_id')->unique();
            $table->unsignedBigInteger('user_id')->nullable();
            $table->json('conversation_history')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamp('last_activity')->nullable();
            $table->timestamps();

            $table->foreign('user_id')->references('id')->on('users');
            $table->index(['user_id', 'is_active']);
        });
    }

    public function down()
    {
        Schema::dropIfExists('chat_sessions');
    }
}
```

## Usage Example

```php
// In your controller or service
$chatbotService = new ChatbotService();

// Start a chat session
$session = $chatbotService->startChatSession();
$sessionId = $session['session_id'];

// Send a message
$response = $chatbotService->sendMessage($sessionId, "I have fever and cough");

// Get predictions
$predictions = $response['predictions'];

// End the session when done
$chatbotService->endChatSession($sessionId);
```

## Error Handling

The service class includes comprehensive error handling. Always check for the `error` key in responses:

```php
$result = $chatbotService->sendMessage($sessionId, $message);

if (isset($result['error'])) {
    // Handle error
    Log::error('Chatbot error: ' . $result['error']);
    return response()->json(['message' => 'Chatbot service unavailable'], 503);
}

// Process successful response
return response()->json($result);
```

## Testing

Create tests for your chatbot integration:

```php
<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Services\ChatbotService;
use Illuminate\Support\Facades\Http;

class ChatbotServiceTest extends TestCase
{
    public function test_can_start_chat_session()
    {
        Http::fake([
            '*/chat/start' => Http::response([
                'session_id' => 'test-session-id',
                'message' => 'Chat session started successfully'
            ])
        ]);

        $service = new ChatbotService();
        $result = $service->startChatSession();

        $this->assertArrayHasKey('session_id', $result);
        $this->assertEquals('test-session-id', $result['session_id']);
    }
}
```

