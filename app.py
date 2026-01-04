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
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_6957e6ae66088195af2b5053af22c7ae0f5f0db59da0747b',
        'prompt_version': '22',
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
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter',
        'lang': 'tr',
        # Turkish UI texts
        'xp_title': 'Seni Tanıma Seviyesi',
        'xp_level': 'Seviye',
        'xp_next': 'Sonraki',
        'xp_max': 'Maksimum Seviye!',
        'timer_set': 'Terapi Süresi Belirle',
        'timer_minute': 'dakika',
        'timer_minutes': 'dakika',
        'timer_custom': 'Kendiniz girin...',
        'timer_start': 'Başlat',
        'timer_ended': 'Süre Doldu!',
        'timer_ended_msg': 'Terapi süreniz tamamlandı. Kendinize ayırdığınız bu zaman için tebrikler! İsterseniz "Seansı Bitir ve Özetle" ile özetinizi alabilirsiniz.',
        'summarize': 'Seansı Bitir ve Özetle',
        'summary_title': 'Seans Özeti',
        'summary_loading': 'Seans özetleniyor...',
        'summary_ok': 'Tamam',
        'online': 'Çevrimiçi',
        'chats': 'Sohbetler',
        'delete_confirm': 'Bu sohbeti silmek istediğinize emin misiniz?',
        'connection_error': 'Bağlantı Hatası',
        'connection_failed': 'Sunucuya bağlanılamadı.',
        'intensity_question': 'Şiddeti nasıl?',
        'intensity_1': 'Hafif',
        'intensity_2': 'Az',
        'intensity_3': 'Orta',
        'intensity_4': 'Yoğun',
        'intensity_5': 'Çok',
        'add_note': 'Eklemek istediğin bir şey var mı?',
        'optional': '(İsteğe bağlı)',
        'cancel': 'İptal',
        'send': 'Gönder',
        'short_msg': 'Kısa Mesaj',
        'medium_msg': 'Orta Mesaj',
        'long_msg': 'Uzun Mesaj',
        'xp_thanks': 'Teşekkürler, seni daha iyi tanıyorum!',
        'level_up_congrats': 'Tebrikler!',
        'level_messages': [
            "Yeni bir yolculuğa başladık!",
            "Seninle olan bağımız güçleniyor. Artık seni daha iyi anlayabiliyorum.",
            "Paylaştıkların bana çok şey öğretiyor. Teşekkürler!",
            "Seni tanımak güzel, derinleşiyoruz.",
            "Birlikte güzel bir yol katetik. Seninle gurur duyuyorum!",
            "Artık seni gerçekten tanıyorum. Bu özel bir bağ.",
            "Senin için daha iyi bir rehber olabiliyorum artık.",
            "Bu seviyeye ulaşan çok az kişi var. Tebrikler!",
            "Seninle olan yolculuğumuz muhteşem!",
            "Maksimum bağlantı! Artık seni çok iyi tanıyorum."
        ]
    },
    'cihan': {
        'id': 'cihan',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_6957fe7589408195b68e4afa711750cb0976d4371a952f32',
        'prompt_version': '8',
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
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter',
        'lang': 'tr',
        'xp_title': 'Seni Tanıma Seviyesi',
        'xp_level': 'Seviye',
        'xp_next': 'Sonraki',
        'xp_max': 'Maksimum Seviye!',
        'timer_set': 'Terapi Süresi Belirle',
        'timer_minute': 'dakika',
        'timer_minutes': 'dakika',
        'timer_custom': 'Kendiniz girin...',
        'timer_start': 'Başlat',
        'timer_ended': 'Süre Doldu!',
        'timer_ended_msg': 'Terapi süreniz tamamlandı. Kendinize ayırdığınız bu zaman için tebrikler!',
        'summarize': 'Seansı Bitir ve Özetle',
        'summary_title': 'Seans Özeti',
        'summary_loading': 'Seans özetleniyor...',
        'summary_ok': 'Tamam',
        'online': 'Çevrimiçi',
        'chats': 'Sohbetler',
        'delete_confirm': 'Bu sohbeti silmek istediğinize emin misiniz?',
        'connection_error': 'Bağlantı Hatası',
        'connection_failed': 'Sunucuya bağlanılamadı.',
        'intensity_question': 'Şiddeti nasıl?',
        'intensity_1': 'Hafif',
        'intensity_2': 'Az',
        'intensity_3': 'Orta',
        'intensity_4': 'Yoğun',
        'intensity_5': 'Çok',
        'add_note': 'Eklemek istediğin bir şey var mı?',
        'optional': '(İsteğe bağlı)',
        'cancel': 'İptal',
        'send': 'Gönder',
        'short_msg': 'Kısa Mesaj',
        'medium_msg': 'Orta Mesaj',
        'long_msg': 'Uzun Mesaj',
        'xp_thanks': 'Teşekkürler, seni daha iyi tanıyorum!',
        'level_up_congrats': 'Tebrikler!'
    },
    'melike': {
        'id': 'melike',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_69580dccde088194aab560e77f08932c0e3a18c90eedd3b9',
        'prompt_version': '8',
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
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_695958416b2081978b087eb082a52f6e031bfc22cd5d10b0',
        'prompt_version': '5',
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
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
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
    },
    'esma': {
        'id': 'esma',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_695abdf6ceb48197b0d9da642a812e2b07ebc6cea3cb0d56',
        'prompt_version': '4',
        'accent_color': '#8b5cf6',  # Purple
        'welcome_title': 'Merhaba Esma! 👋',
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
        'input_hint': 'Göndermek için Enter, yeni satır için Shift+Enter',
        'lang': 'tr',
        # Turkish UI texts
        'xp_title': 'Seni Tanıma Seviyesi',
        'xp_level': 'Seviye',
        'xp_next': 'Sonraki',
        'xp_max': 'Maksimum Seviye!',
        'timer_set': 'Terapi Süresi Belirle',
        'timer_minute': 'dakika',
        'timer_minutes': 'dakika',
        'timer_custom': 'Kendiniz girin...',
        'timer_start': 'Başlat',
        'timer_ended': 'Süre Doldu!',
        'timer_ended_msg': 'Terapi süreniz tamamlandı. Kendinize ayırdığınız bu zaman için tebrikler! İsterseniz "Seansı Bitir ve Özetle" ile özetinizi alabilirsiniz.',
        'summarize': 'Seansı Bitir ve Özetle',
        'summary_title': 'Seans Özeti',
        'summary_loading': 'Seans özetleniyor...',
        'summary_ok': 'Tamam',
        'online': 'Çevrimiçi',
        'chats': 'Sohbetler',
        'delete_confirm': 'Bu sohbeti silmek istediğinize emin misiniz?',
        'connection_error': 'Bağlantı Hatası',
        'connection_failed': 'Sunucuya bağlanılamadı.',
        'intensity_question': 'Şiddeti nasıl?',
        'intensity_1': 'Hafif',
        'intensity_2': 'Az',
        'intensity_3': 'Orta',
        'intensity_4': 'Yoğun',
        'intensity_5': 'Çok',
        'add_note': 'Eklemek istediğin bir şey var mı?',
        'optional': '(İsteğe bağlı)',
        'cancel': 'İptal',
        'send': 'Gönder',
        'short_msg': 'Kısa Mesaj',
        'medium_msg': 'Orta Mesaj',
        'long_msg': 'Uzun Mesaj',
        'xp_thanks': 'Teşekkürler, seni daha iyi tanıyorum!',
        'level_up_congrats': 'Tebrikler!',
        'level_messages': [
            "Yeni bir yolculuğa başladık!",
            "Seninle olan bağımız güçleniyor. Artık seni daha iyi anlayabiliyorum.",
            "Paylaştıkların bana çok şey öğretiyor. Teşekkürler!",
            "Seni tanımak güzel, derinleşiyoruz.",
            "Birlikte güzel bir yol katetik. Seninle gurur duyuyorum!",
            "Artık seni gerçekten tanıyorum. Bu özel bir bağ.",
            "Senin için daha iyi bir rehber olabiliyorum artık.",
            "Bu seviyeye ulaşan çok az kişi var. Tebrikler!",
            "Seninle olan yolculuğumuz muhteşem!",
            "Maksimum bağlantı! Artık seni çok iyi tanıyorum."
        ]
    },
    'warriorsofcompassion': {
        'id': 'warriorsofcompassion',
        'name': 'Symbiont',
        'short_name': 'Symbiont',
        'icon': '🧠',
        'logo': '/static/logo-symbiont.png',
        'prompt_id': 'pmpt_6959a81350a081958e0480a132d5143605ab6f540d752f0f',
        'prompt_version': '2',
        'accent_color': '#10a37f',  # Green
        'welcome_title': 'Hello Warriors of Compassion! 👋',
        'welcome_text': "What's dominating right now?",
        'suggestions': [
            {'display': '😰 Rising anxiety', 'message': "I'm feeling rising anxiety right now."},
            {'display': '🌊 Panic wave', 'message': "I feel like a panic wave is coming."},
            {'display': '🌀 Racing thoughts', 'message': "My thoughts keep racing non-stop."},
            {'display': '🛏️ Sleep lock', 'message': "I'm experiencing sleep lock, can't fall asleep."},
            {'display': '🎯 Focus scatter', 'message': "I'm experiencing scattered focus."},
            {'display': '⏰ Procrastination urge', 'message': "I'm feeling the urge to procrastinate."},
            {'display': '🚧 Decision block', 'message': "I'm struggling to make decisions, feeling stuck."},
            {'display': '💨 Inner tension', 'message': "I'm feeling tension inside."},
            {'display': '🔥 Anger surge', 'message': "I feel anger rising inside me."},
            {'display': '🌑 Loneliness', 'message': "I'm feeling lonely."}
        ],
        'input_placeholder': 'Type your message...',
        'new_chat': 'New Chat',
        'today': 'Today',
        'yesterday': 'Yesterday',
        'previous': 'Previous',
        'no_chats': 'No chats yet',
        'input_hint': 'Press Enter to send, Shift+Enter for new line',
        'lang': 'en',
        # English UI texts
        'xp_title': 'Understanding Level',
        'xp_level': 'Level',
        'xp_next': 'Next',
        'xp_max': 'Maximum Level!',
        'timer_set': 'Set Therapy Duration',
        'timer_minute': 'minute',
        'timer_minutes': 'minutes',
        'timer_custom': 'Enter custom...',
        'timer_start': 'Start',
        'timer_ended': 'Time is up!',
        'timer_ended_msg': 'Your therapy session is complete. Congratulations on taking this time for yourself! You can use "End & Summarize" to get your session summary.',
        'summarize': 'End & Summarize Session',
        'summary_title': 'Session Summary',
        'summary_loading': 'Summarizing session...',
        'summary_ok': 'OK',
        'online': 'Online',
        'chats': 'Chats',
        'delete_confirm': 'Are you sure you want to delete this chat?',
        'connection_error': 'Connection Error',
        'connection_failed': 'Could not connect to server.',
        'intensity_question': "How intense is it?",
        'intensity_1': 'Very Mild',
        'intensity_2': 'Mild',
        'intensity_3': 'Moderate',
        'intensity_4': 'Intense',
        'intensity_5': 'Very Intense',
        'add_note': 'Anything you want to add?',
        'optional': '(Optional)',
        'cancel': 'Cancel',
        'send': 'Send',
        'short_msg': 'Short Message',
        'medium_msg': 'Medium Message',
        'long_msg': 'Long Message',
        'xp_thanks': 'Thanks, I understand you better!',
        'level_up_congrats': 'Congratulations!',
        'level_messages': [
            "A new journey begins!",
            "Our connection is growing stronger. I can understand you better now.",
            "What you share teaches me a lot. Thank you!",
            "Getting to know you is wonderful, we're going deeper.",
            "We've come a long way together. I'm proud of you!",
            "I truly know you now. This is a special bond.",
            "I can be a better guide for you now.",
            "Very few reach this level. Congratulations!",
            "Our journey together is amazing!",
            "Maximum connection! I know you very well now."
        ]
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

@app.route('/esma')
def esma_chat():
    """Esma-AI chat page."""
    return render_template('chat.html', bot=CHATBOTS['esma'])

@app.route('/warriorsofcompassion')
def warriorsofcompassion_chat():
    """Warriors of Compassion English chat page."""
    return render_template('chat.html', bot=CHATBOTS['warriorsofcompassion'])

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

# Session Summary Prompts
SESSION_SUMMARY_PROMPT_TR = """Sen bir terapi seansı özetleyicisisin. Aşağıdaki seans konuşmasını analiz et ve TAM OLARAK şu formatta yanıt ver:

**📝 Özet:** [Seansın ana temasını ve kullanıcının durumunu özetleyen TEK bir cümle]

**🎯 Aksiyon:** [Kullanıcının yapabileceği somut, küçük ve yapılabilir TEK bir adım]

**💚 Kendine Not:** [Kendine şefkat veya gerçekçilik içeren, destekleyici TEK bir cümle]

Kurallar:
- Her bölüm MUTLAKA tek cümle olmalı
- Özet cümlesi seans başlığı olarak da kullanılacak, bu yüzden kısa ve öz olsun (max 50 karakter)
- Aksiyon somut ve hemen uygulanabilir olmalı
- Kendine not kısmı sıcak ve destekleyici olmalı
- Türkçe yaz"""

SESSION_SUMMARY_PROMPT_EN = """You are a therapy session summarizer. Analyze the following session conversation and respond in EXACTLY this format:

**📝 Summary:** [ONE sentence summarizing the main theme and user's state in the session]

**🎯 Action:** [ONE specific, small, and actionable step the user can take]

**💚 Note to Self:** [ONE supportive sentence with self-compassion or realistic encouragement]

Rules:
- Each section MUST be exactly one sentence
- The summary sentence will also be used as the chat title, so keep it short and concise (max 50 characters)
- The action must be concrete and immediately applicable
- The note to self should be warm and supportive
- Write in English"""

@app.route('/api/conversations/<conversation_id>/summarize', methods=['POST'])
def summarize_session(conversation_id):
    """Generate a session summary for a conversation."""
    # Get bot_id from request to determine language
    data = request.get_json() or {}
    bot_id = data.get('bot_id', '')
    
    # Determine language from bot config
    bot_config = CHATBOTS.get(bot_id, {})
    is_english = bot_config.get('lang') == 'en'
    
    # Get conversation messages
    messages = db.get_messages(conversation_id)
    if not messages:
        error_msg = 'No messages to summarize.' if is_english else 'Özetlenecek mesaj bulunamadı.'
        return jsonify({
            'error': 'No messages',
            'error_type': 'validation_error',
            'details': error_msg
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
    if is_english:
        conversation_text = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in messages
        ])
        summary_prompt = SESSION_SUMMARY_PROMPT_EN
        user_prompt = f"Summarize this session:\n\n{conversation_text}"
    else:
        conversation_text = "\n".join([
            f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}"
            for m in messages
        ])
        summary_prompt = SESSION_SUMMARY_PROMPT_TR
        user_prompt = f"Şu seansı özetle:\n\n{conversation_text}"
    
    try:
        # Call OpenAI API for summary
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        summary_text = response.choices[0].message.content
        
        # Extract the summary line for title
        # Works for both "📝 Özet:" (Turkish) and "📝 Summary:" (English)
        title_match = summary_text.split("**📝 Özet:**") if not is_english else summary_text.split("**📝 Summary:**")
        if len(title_match) > 1:
            # Get the text after "Özet:/Summary:" until the next section or newline
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

# ============== XP System API ==============

@app.route('/api/xp/<bot_id>', methods=['GET'])
def get_xp(bot_id):
    """Get XP data for a user."""
    xp_data = db.get_user_xp(bot_id)
    return jsonify(xp_data)

@app.route('/api/xp/<bot_id>', methods=['POST'])
def add_xp_endpoint(bot_id):
    """Add XP for a user."""
    data = request.json
    xp_amount = data.get('xp', 0)
    
    if xp_amount <= 0:
        return jsonify({'error': 'Invalid XP amount'}), 400
    
    xp_data = db.add_xp(bot_id, xp_amount)
    return jsonify(xp_data)

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', 8080))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
