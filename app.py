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
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧠',
        'prompt_id': 'pmpt_6957e6ae66088195af2b5053af22c7ae0f5f0db59da0747b',
        'prompt_version': '20',
        'accent_color': '#10a37f',  # Green
        'welcome_title': 'Merhaba Meliksah! 👋',
        'welcome_text': 'Şu an baskın olan hangisi?',
        'suggestions': [
            {'display': '😰 Yükselen kaygı', 'message': 'Şu an yükselen bir kaygı hissediyorum.'},
            {'display': '🌊 Panik dalgası', 'message': 'Bir panik dalgası geliyor gibi hissediyorum.'},
            {'display': '🌀 Durmayan düşünceler', 'message': 'Düşüncelerim durmadan dönüyor.'},
            {'display': '🛏️ Uyku kilidi', 'message': 'Uyku kilidi yaşıyorum, uyuyamıyorum.'},
            {'display': '🎯 Odak dağınıklığı', 'message': 'Odak dağınıklığı yaşıyorum.'},
            {'display': '⏰ Erteleme dürtüsü', 'message': 'Erteleme dürtüsü hissediyorum.'},
            {'display': '🚧 Karar tıkanması', 'message': 'Karar vermekte zorlanıyorum, tıkandım.'},
            {'display': '💨 İç sıkışma', 'message': 'İçimde bir sıkışma hissediyorum.'},
            {'display': '🔥 Öfke patlaması', 'message': 'İçimde yükselen bir öfke var.'},
            {'display': '🌑 Yalnızlık hissi', 'message': 'Kendimi yalnız hissediyorum.'}
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
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🤖',
        'prompt_id': 'pmpt_6957fe7589408195b68e4afa711750cb0976d4371a952f32',
        'prompt_version': '7',
        'accent_color': '#6366f1',  # Purple/Indigo
        'welcome_title': 'Merhaba Cihan! 👋',
        'welcome_text': 'Şu an baskın olan hangisi?',
        'suggestions': [
            {'display': '😰 Yükselen kaygı', 'message': 'Şu an yükselen bir kaygı hissediyorum.'},
            {'display': '🌊 Panik dalgası', 'message': 'Bir panik dalgası geliyor gibi hissediyorum.'},
            {'display': '🌀 Durmayan düşünceler', 'message': 'Düşüncelerim durmadan dönüyor.'},
            {'display': '🛏️ Uyku kilidi', 'message': 'Uyku kilidi yaşıyorum, uyuyamıyorum.'},
            {'display': '🎯 Odak dağınıklığı', 'message': 'Odak dağınıklığı yaşıyorum.'},
            {'display': '⏰ Erteleme dürtüsü', 'message': 'Erteleme dürtüsü hissediyorum.'},
            {'display': '🚧 Karar tıkanması', 'message': 'Karar vermekte zorlanıyorum, tıkandım.'},
            {'display': '💨 İç sıkışma', 'message': 'İçimde bir sıkışma hissediyorum.'},
            {'display': '🔥 Öfke patlaması', 'message': 'İçimde yükselen bir öfke var.'},
            {'display': '🌑 Yalnızlık hissi', 'message': 'Kendimi yalnız hissediyorum.'}
        ],
        'input_placeholder': 'Mesajını yaz...',
        'new_chat': 'Yeni Sohbet',
        'today': 'Bugün',
        'yesterday': 'Dün',
        'previous': 'Önceki',
        'no_chats': 'Henüz sohbet yok',
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter'
    },
    'melike': {
        'id': 'melike',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '💜',
        'prompt_id': 'pmpt_69580dccde088194aab560e77f08932c0e3a18c90eedd3b9',
        'prompt_version': '6',
        'accent_color': '#ec4899',  # Pink
        'welcome_title': 'Merhaba Melike! 👋',
        'welcome_text': 'Şu an baskın olan hangisi?',
        'suggestions': [
            {'display': '😰 Yükselen kaygı', 'message': 'Şu an yükselen bir kaygı hissediyorum.'},
            {'display': '🌊 Panik dalgası', 'message': 'Bir panik dalgası geliyor gibi hissediyorum.'},
            {'display': '🌀 Durmayan düşünceler', 'message': 'Düşüncelerim durmadan dönüyor.'},
            {'display': '🛏️ Uyku kilidi', 'message': 'Uyku kilidi yaşıyorum, uyuyamıyorum.'},
            {'display': '🎯 Odak dağınıklığı', 'message': 'Odak dağınıklığı yaşıyorum.'},
            {'display': '⏰ Erteleme dürtüsü', 'message': 'Erteleme dürtüsü hissediyorum.'},
            {'display': '🚧 Karar tıkanması', 'message': 'Karar vermekte zorlanıyorum, tıkandım.'},
            {'display': '💨 İç sıkışma', 'message': 'İçimde bir sıkışma hissediyorum.'},
            {'display': '🔥 Öfke patlaması', 'message': 'İçimde yükselen bir öfke var.'},
            {'display': '🌑 Yalnızlık hissi', 'message': 'Kendimi yalnız hissediyorum.'}
        ],
        'input_placeholder': 'Mesajını yaz...',
        'new_chat': 'Yeni Sohbet',
        'today': 'Bugün',
        'yesterday': 'Dün',
        'previous': 'Önceki',
        'no_chats': 'Henüz sohbet yok',
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter'
    },
    'eda': {
        'id': 'eda',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧡',
        'prompt_id': 'pmpt_695958416b2081978b087eb082a52f6e031bfc22cd5d10b0',
        'prompt_version': '3',
        'accent_color': '#f97316',  # Orange
        'welcome_title': 'Merhaba Eda! 👋',
        'welcome_text': 'Şu an baskın olan hangisi?',
        'suggestions': [
            {'display': '😰 Yükselen kaygı', 'message': 'Şu an yükselen bir kaygı hissediyorum.'},
            {'display': '🌊 Panik dalgası', 'message': 'Bir panik dalgası geliyor gibi hissediyorum.'},
            {'display': '🌀 Durmayan düşünceler', 'message': 'Düşüncelerim durmadan dönüyor.'},
            {'display': '🛏️ Uyku kilidi', 'message': 'Uyku kilidi yaşıyorum, uyuyamıyorum.'},
            {'display': '🎯 Odak dağınıklığı', 'message': 'Odak dağınıklığı yaşıyorum.'},
            {'display': '⏰ Erteleme dürtüsü', 'message': 'Erteleme dürtüsü hissediyorum.'},
            {'display': '🚧 Karar tıkanması', 'message': 'Karar vermekte zorlanıyorum, tıkandım.'},
            {'display': '💨 İç sıkışma', 'message': 'İçimde bir sıkışma hissediyorum.'},
            {'display': '🔥 Öfke patlaması', 'message': 'İçimde yükselen bir öfke var.'},
            {'display': '🌑 Yalnızlık hissi', 'message': 'Kendimi yalnız hissediyorum.'}
        ],
        'input_placeholder': 'Mesajını yaz...',
        'new_chat': 'Yeni Sohbet',
        'today': 'Bugün',
        'yesterday': 'Dün',
        'previous': 'Önceki',
        'no_chats': 'Henüz sohbet yok',
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter'
    },
    'can': {
        'id': 'can',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🔵',
        'prompt_id': 'pmpt_69596825aeec819093917a7d6078509801eec0b63cd76647',
        'prompt_version': '2',
        'accent_color': '#3b82f6',  # Blue
        'welcome_title': 'Merhaba Can! 👋',
        'welcome_text': 'Şu an baskın olan hangisi?',
        'suggestions': [
            {'display': '😰 Yükselen kaygı', 'message': 'Şu an yükselen bir kaygı hissediyorum.'},
            {'display': '🌊 Panik dalgası', 'message': 'Bir panik dalgası geliyor gibi hissediyorum.'},
            {'display': '🌀 Durmayan düşünceler', 'message': 'Düşüncelerim durmadan dönüyor.'},
            {'display': '🛏️ Uyku kilidi', 'message': 'Uyku kilidi yaşıyorum, uyuyamıyorum.'},
            {'display': '🎯 Odak dağınıklığı', 'message': 'Odak dağınıklığı yaşıyorum.'},
            {'display': '⏰ Erteleme dürtüsü', 'message': 'Erteleme dürtüsü hissediyorum.'},
            {'display': '🚧 Karar tıkanması', 'message': 'Karar vermekte zorlanıyorum, tıkandım.'},
            {'display': '💨 İç sıkışma', 'message': 'İçimde bir sıkışma hissediyorum.'},
            {'display': '🔥 Öfke patlaması', 'message': 'İçimde yükselen bir öfke var.'},
            {'display': '🌑 Yalnızlık hissi', 'message': 'Kendimi yalnız hissediyorum.'}
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

@app.route('/melike')
def melike_chat():
    """Melike-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['melike'])

@app.route('/eda')
def eda_chat():
    """Eda-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['eda'])

@app.route('/can')
def can_chat():
    """Can-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['can'])

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

# Session Summary Prompt
SESSION_SUMMARY_PROMPT = """Sen bir terapi seansı özetleyicisisin. Aşağıdaki seans konuşmasını analiz et ve TAM OLARAK şu formatta yanıt ver:

**📝 Özet:** [Seansın ana temasını ve kullanıcının durumunu özetleyen TEK bir cümle]

**🎯 Aksiyon:** [Kullanıcının yapabileceği somut, küçük ve yapılabilir TEK bir adım]

**💚 Kendine Not:** [Kendine şefkat veya gerçekçilik içeren, destekleyici TEK bir cümle]

Kurallar:
- Her bölüm MUTLAKA tek cümle olmalı
- Özet cümlesi seans başlığı olarak da kullanılacak, bu yüzden kısa ve öz olsun (max 50 karakter)
- Aksiyon somut ve hemen uygulanabilir olmalı
- Kendine not kısmı sıcak ve destekleyici olmalı
- Türkçe yaz"""

@app.route('/api/conversations/<conversation_id>/summarize', methods=['POST'])
def summarize_session(conversation_id):
    """Generate a session summary for a conversation."""
    bot_id = request.json.get('bot_id', 'meliksah') if request.json else 'meliksah'
    
    # Only allow for meliksah for now
    if bot_id != 'meliksah':
        return jsonify({
            'error': 'Feature not available',
            'error_type': 'feature_error',
            'details': 'Bu özellik şu an sadece belirli kullanıcılar için aktif.'
        }), 403
    
    # Get conversation messages
    messages = db.get_messages(conversation_id)
    if not messages:
        return jsonify({
            'error': 'No messages',
            'error_type': 'validation_error',
            'details': 'Özetlenecek mesaj bulunamadı.'
        }), 400
    
    # Check if API key is configured
    client = get_openai_client()
    if client is None:
        return jsonify({
            'error': 'API key not configured',
            'error_type': 'config_error',
            'details': 'OpenAI API key is missing.'
        }), 500
    
    # Build conversation text for summary
    conversation_text = "\n".join([
        f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}"
        for m in messages
    ])
    
    try:
        # Call OpenAI API for summary
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SESSION_SUMMARY_PROMPT},
                {"role": "user", "content": f"Şu seansı özetle:\n\n{conversation_text}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        summary_text = response.choices[0].message.content
        
        # Extract the summary line for title (first line after "📝 Özet:")
        title_match = summary_text.split("**📝 Özet:**")
        if len(title_match) > 1:
            # Get the text after "Özet:" until the next section or newline
            title_part = title_match[1].split("**🎯")[0].strip()
            # Clean up and limit length
            new_title = title_part.replace("\n", " ").strip()[:60]
            if new_title:
                db.update_conversation_title(conversation_id, new_title)
        
        return jsonify({
            'summary': summary_text,
            'conversation_id': conversation_id
        })
        
    except AuthenticationError as e:
        return jsonify({
            'error': 'Authentication failed',
            'error_type': 'auth_error',
            'details': 'API key geçersiz.'
        }), 401
    except RateLimitError as e:
        return jsonify({
            'error': 'Rate limit',
            'error_type': 'rate_limit_error',
            'details': 'Çok fazla istek. Lütfen biraz bekleyin.'
        }), 429
    except Exception as e:
        print(f"Summary Error: {e}")
        return jsonify({
            'error': 'Summary failed',
            'error_type': 'api_error',
            'details': f'Özet oluşturulamadı: {str(e)}'
        }), 500

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
