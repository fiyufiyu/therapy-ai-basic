# Admin Endpoint Kurulumu

## Contact Preferences Verilerini Görüntüleme

Contact preferences verileri korumalı bir admin endpoint'inde saklanır.

### 1. Local Development'ta

`.env` dosyanıza ekleyin:

```bash
ADMIN_TOKEN=your-secret-admin-token-here-12345
```

**Önemli:** Güçlü bir token kullanın! Örnek:
```bash
ADMIN_TOKEN=sk_admin_aB3xK9mPqR7sT2vL8nW4jF6hY1cD5eG0
```

### 2. Railway'de (Production)

1. Railway Dashboard'a gidin
2. Projenizi seçin
3. **Variables** sekmesine tıklayın
4. Yeni bir variable ekleyin:
   - **Key:** `ADMIN_TOKEN`
   - **Value:** `your-secret-admin-token-here-12345`
5. Deploy edin

### 3. API Kullanımı

**Endpoint:** `GET /api/contact-preferences`

**Header gerekli:**
```
Authorization: Bearer your-secret-admin-token-here-12345
```

#### cURL ile Örnek:

```bash
# Local
curl -H "Authorization: Bearer your-secret-admin-token-here-12345" \
     http://localhost:8080/api/contact-preferences

# Production
curl -H "Authorization: Bearer your-secret-admin-token-here-12345" \
     https://your-app.railway.app/api/contact-preferences
```

#### Postman ile:

1. Request Type: **GET**
2. URL: `http://localhost:8080/api/contact-preferences`
3. Headers:
   - Key: `Authorization`
   - Value: `Bearer your-secret-admin-token-here-12345`

#### JavaScript ile:

```javascript
fetch('http://localhost:8080/api/contact-preferences', {
  headers: {
    'Authorization': 'Bearer your-secret-admin-token-here-12345'
  }
})
.then(res => res.json())
.then(data => console.log(data));
```

### 4. Yanıt Formatı

```json
{
  "preferences": [
    {
      "bot_id": "meliksah",
      "bot_name": "Symbiont",
      "email": "user@example.com",
      "phone": "+90 555 123 45 67",
      "frequency": 4,
      "created_at": "2026-01-10T00:15:30.123Z",
      "updated_at": "2026-01-10T00:15:30.123Z"
    }
  ],
  "count": 1
}
```

### 5. Hata Kodları

- **401 Unauthorized:** Token eksik veya yanlış
- **500 Internal Server Error:** ADMIN_TOKEN environment variable ayarlanmamış

## Güvenlik Notları

1. ⚠️ **ADMIN_TOKEN'ı asla GitHub'a commit etmeyin!**
2. ⚠️ `.env` dosyası `.gitignore`'da olmalı
3. ⚠️ Her ortam için farklı token kullanın (dev, staging, production)
4. ✅ Güçlü, tahmin edilemez tokenlar kullanın
5. ✅ Tokenları düzenli olarak değiştirin
