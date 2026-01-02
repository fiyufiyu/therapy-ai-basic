# 🧠 Kişisel AI Asistan

Meliksah ve Cihan için özel olarak tasarlanmış AI asistan uygulaması.

## 🌐 Canlı Demo

- **Meliksah için Asistan**: `/meliksah`
- **Cihan için Asistan**: `/cihan`

## ✨ Özellikler

- 🎨 Modern ve kullanıcı dostu arayüz
- 💬 Gerçek zamanlı sohbet
- 📱 Mobil uyumlu tasarım
- 💾 Sohbet geçmişi kaydetme
- ⏱️ Yanıt süresi gösterimi
- 🌙 Kişiye özel temalar

## 🚀 Railway'e Deploy

### 1. Railway Hesabı Oluştur
[railway.app](https://railway.app) adresinden hesap oluştur.

### 2. Yeni Proje Oluştur
- "New Project" → "Deploy from GitHub repo"
- Bu repository'yi seç

### 3. Environment Variable Ekle
Railway dashboard'da:
```
OPENAI_API_KEY=sk-proj-xxxxx
```

### 4. Deploy!
Railway otomatik olarak deploy edecek. Birkaç dakika içinde canlı olacak.

## 🛠️ Lokal Geliştirme

### Gereksinimler
- Python 3.9+
- OpenAI API key

### Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/YOUR_USERNAME/therapy-ai-basic.git
cd therapy-ai-basic

# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyası oluştur
echo "OPENAI_API_KEY=sk-proj-xxxxx" > .env

# Çalıştır
python app.py
```

Tarayıcıda aç: http://localhost:8080

## 📁 Proje Yapısı

```
therapy-ai-basic/
├── app.py              # Flask uygulaması
├── database.py         # SQLite veritabanı işlemleri
├── templates/
│   └── chat.html       # Chat arayüzü
├── requirements.txt    # Python bağımlılıkları
├── Procfile           # Gunicorn yapılandırması
├── railway.json       # Railway yapılandırması
└── README.md
```

## ⚙️ Yapılandırma

### Chatbot Ayarları

`app.py` dosyasındaki `CHATBOTS` dictionary'sinden her bot için:
- İsim ve ikon
- OpenAI prompt ID
- Tema rengi
- Karşılama mesajları
- Öneri butonları

düzenlenebilir.

## 🔐 Güvenlik

- API key'i asla koda ekleme, environment variable kullan
- `.env` dosyası `.gitignore`'da olmalı
- Production'da debug modunu kapat

## 📝 Lisans

Bu proje kişisel kullanım içindir.

---

Made with ❤️ using Flask & OpenAI

