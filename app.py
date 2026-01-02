from flask import Flask, request, jsonify, render_template, redirect
from openai import OpenAI, APIError, AuthenticationError, RateLimitError, APIConnectionError
from dotenv import load_dotenv
import os
import time
import database as db

load_dotenv()

app = Flask(__name__)

# Initialize database
db.init_db()

# Lazy OpenAI client initialization
_client = None

def get_openai_client():
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"DEBUG: API key exists: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
        if api_key:
            _client = OpenAI(api_key=api_key)
    return _client

@app.route('/api/debug')
def debug_env():
    """Debug endpoint to check environment variables."""
    api_key = os.getenv('OPENAI_API_KEY')
    return jsonify({
        'api_key_exists': bool(api_key),
        'api_key_length': len(api_key) if api_key else 0,
        'api_key_prefix': api_key[:10] + '...' if api_key and len(api_key) > 10 else None,
        'env_vars': list(os.environ.keys())
    })

# ============== Chatbot Configurations ==============

CHATBOTS = {
    'meliksah': {
        'id': 'meliksah',
        'name': 'Meliksah için Asistan',
        'short_name': 'Asistan',
        'icon': '🧠',
        'prompt_id': 'pmpt_6957e6ae66088195af2b5053af22c7ae0f5f0db59da0747b',
        'prompt_version': '18',
        'accent_color': '#10a37f',  # Green
        'welcome_title': 'Merhaba Meliksah! 👋',
        'welcome_text': 'Bugün sana nasıl yardımcı olabilirim? Aklındaki her şeyi benimle paylaşabilirsin.',
        'suggestions': [
            'Son zamanlarda kendimi stresli hissediyorum',
            'Biraz sohbet etmek istiyorum',
            'Kendimi geliştirmek istiyorum'
        ],
        'input_placeholder': 'Mesajını yaz...',
        'new_chat': 'Yeni Sohbet',
        'today': 'Bugün',
        'yesterday': 'Dün',
        'previous': 'Önceki',
        'no_chats': 'Henüz sohbet yok',
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter'
    },
    'cihan': {
        'id': 'cihan',
        'name': 'Cihan için Asistan',
        'short_name': 'Asistan',
        'icon': '🤖',
        'prompt_id': 'pmpt_6957fe7589408195b68e4afa711750cb0976d4371a952f32',
        'prompt_version': '6',
        'accent_color': '#6366f1',  # Purple/Indigo
        'welcome_title': 'Merhaba Cihan! 👋',
        'welcome_text': 'Bugün sana nasıl yardımcı olabilirim? İstediğin her konuda yanındayım.',
        'suggestions': [
            'Bugün nasıl hissediyorum anlatayım',
            'Bir konuda tavsiye almak istiyorum',
            'Sadece sohbet edelim'
        ],
        'input_placeholder': 'Mesajını yaz...',
        'new_chat': 'Yeni Sohbet',
        'today': 'Bugün',
        'yesterday': 'Dün',
        'previous': 'Önceki',
        'no_chats': 'Henüz sohbet yok',
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter'
    }
}

# ============== Page Routes ==============

@app.route('/')
def index():
    """Redirect to default chatbot."""
    return redirect('/meliksah')

@app.route('/meliksah')
def meliksah_chat():
    """Meliksah-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['meliksah'])

@app.route('/cihan')
def cihan_chat():
    """Cihan-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['cihan'])

# ============== Chat API ==============

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    bot_id = data.get('bot_id', 'meliksah')
    
    # Get bot configuration
    bot = CHATBOTS.get(bot_id)
    if not bot:
        return jsonify({
            'error': 'Invalid bot',
            'error_type': 'validation_error',
            'details': f'Bot "{bot_id}" not found.'
        }), 400
    
    # Check if prompt is configured
    if not bot['prompt_id']:
        return jsonify({
            'error': 'Bot not configured',
            'error_type': 'config_error',
            'details': f'{bot["name"]} prompt is not configured yet.'
        }), 500
    
    if not user_message:
        return jsonify({
            'error': 'No message provided',
            'error_type': 'validation_error',
            'details': 'Please enter a message before sending.'
        }), 400
    
    # Check if API key is configured
    client = get_openai_client()
    if client is None:
        return jsonify({
            'error': 'API key not configured',
            'error_type': 'config_error',
            'details': 'OpenAI API key is missing. Please add OPENAI_API_KEY environment variable.'
        }), 500
    
    # Add user message to database
    db.add_message(session_id, 'user', user_message, bot_id=bot_id)
    
    # Get conversation history for API
    conversation_history = db.get_messages_for_api(session_id)
    
    try:
        # Measure response time
        start_time = time.time()
        
        # Use the OpenAI API with the bot's prompt
        response = client.responses.create(
            prompt={
                "id": bot['prompt_id'],
                "version": bot['prompt_version']
            },
            input=conversation_history
        )
        
        # Calculate response time in seconds
        response_time = int(time.time() - start_time)
        
        # Extract the response text
        assistant_message = response.output_text
        
        # Add assistant response to database with response time
        db.add_message(session_id, 'assistant', assistant_message, response_time)
        
        return jsonify({
            'response': assistant_message,
            'session_id': session_id,
            'response_time': response_time
        })
    
    except AuthenticationError as e:
        # Remove the failed message from database
        messages = db.get_messages(session_id)
        if messages:
            db.clear_messages(session_id)
            # Re-add all messages except the last one
            for msg in messages[:-1]:
                db.add_message(session_id, msg['role'], msg['content'])
        
        print(f"Authentication Error: {e}")
        return jsonify({
            'error': 'Authentication failed',
            'error_type': 'auth_error',
            'details': 'Your OpenAI API key is invalid or expired. Please check your API key in the .env file.',
            'raw_error': str(e)
        }), 401
    
    except RateLimitError as e:
        # Remove the failed message
        messages = db.get_messages(session_id)
        if messages:
            db.clear_messages(session_id)
            for msg in messages[:-1]:
                db.add_message(session_id, msg['role'], msg['content'])
        
        print(f"Rate Limit Error: {e}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'error_type': 'rate_limit_error',
            'details': 'Too many requests. Please wait a moment and try again. You may have exceeded your OpenAI quota.',
            'raw_error': str(e)
        }), 429
    
    except APIConnectionError as e:
        messages = db.get_messages(session_id)
        if messages:
            db.clear_messages(session_id)
            for msg in messages[:-1]:
                db.add_message(session_id, msg['role'], msg['content'])
        
        print(f"Connection Error: {e}")
        return jsonify({
            'error': 'Connection failed',
            'error_type': 'connection_error',
            'details': 'Could not connect to OpenAI servers. Please check your internet connection.',
            'raw_error': str(e)
        }), 503
    
    except APIError as e:
        messages = db.get_messages(session_id)
        if messages:
            db.clear_messages(session_id)
            for msg in messages[:-1]:
                db.add_message(session_id, msg['role'], msg['content'])
        
        print(f"API Error: {e}")
        return jsonify({
            'error': 'OpenAI API error',
            'error_type': 'api_error',
            'details': f'OpenAI returned an error: {e.message if hasattr(e, "message") else str(e)}',
            'raw_error': str(e)
        }), 500
        
    except Exception as e:
        messages = db.get_messages(session_id)
        if messages:
            db.clear_messages(session_id)
            for msg in messages[:-1]:
                db.add_message(session_id, msg['role'], msg['content'])
        
        print(f"Unexpected Error: {e}")
        return jsonify({
            'error': 'Unexpected error',
            'error_type': 'unknown_error',
            'details': f'An unexpected error occurred: {str(e)}',
            'raw_error': str(e)
        }), 500

# ============== Conversation Management API ==============

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the sidebar."""
    bot_id = request.args.get('bot_id', 'meliksah')
    conversations = db.get_conversations_by_bot(bot_id)
    return jsonify(conversations)

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with its messages."""
    conversation = db.get_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    messages = db.get_messages(conversation_id)
    return jsonify({
        'conversation': conversation,
        'messages': messages
    })

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation."""
    db.delete_conversation(conversation_id)
    return jsonify({'status': 'deleted'})

@app.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
def update_title(conversation_id):
    """Update conversation title."""
    data = request.json
    title = data.get('title', '')
    if title:
        db.update_conversation_title(conversation_id, title)
    return jsonify({'status': 'updated'})

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """Clear messages from a conversation (legacy endpoint)."""
    data = request.json
    session_id = data.get('session_id', 'default')
    db.clear_messages(session_id)
    return jsonify({'status': 'cleared'})

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', 8080))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
