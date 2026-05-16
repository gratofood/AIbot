# 🤖 AI Chatbot — Bizneslar uchun (Gemini AI)

Telegram bot + Google Gemini AI = Sizning biznesingiz uchun 24/7 ishlaydigan AI assistant.

## ⚡ 5 daqiqada ishga tushirish

### 1. Python o'rnating (agar yo'q bo'lsa)
[python.org](https://python.org/downloads/) dan yuklab oling (3.10+).

### 2. Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 3. Telegram token oling
1. Telegramda **@BotFather** ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: SarvinoyBot)
4. Token olasiz — uni `.env` faylga qo'ying

### 4. Gemini API kalit oling (BEPUL!)
1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) ga kiring
2. Google hisobingiz bilan kiring
3. **"Create API Key"** tugmasini bosing
4. Kalitni nusxalab `.env` faylga qo'ying

### 5. `.env` faylni to'ldiring
```env
TELEGRAM_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 6. `bot.py` da biznes ma'lumotlarini o'zgartiring
```python
BIZNES_NOMI = "Sizning biznesingiz nomi"
BIZNES_TELEFON = "+998 90 XXX XX XX"
# BIZNES_MALUMOT ichida narx va xizmatlarni o'zgartiring
```

### 7. Botni ishga tushiring
```bash
python bot.py
```

## 📁 Fayl tuzilmasi
```
AI bot/
├── bot.py            # Asosiy bot kodi (Gemini AI)
├── .env              # API kalitlar (MAXFIY — GitHub ga yuklamang!)
├── .gitignore        # .env ni himoya qiladi
├── requirements.txt  # Kerakli kutubxonalar
└── README.md         # Ushbu qo'llanma
```

## 🛡️ Xavfsizlik
- API kalitlar `.env` faylda saqlanadi
- `.gitignore` `.env` ni GitHub ga yuklamaydi
- Spam himoyasi (rate limiting) mavjud

## ✨ Imkoniyatlar
- 🧠 Suhbat tarixi — bot oldingi xabarlarni eslaydi
- 🛡️ Spam himoyasi — sekundiga 1 dan ortiq xabar qabul qilmaydi
- 📋 Xato loglash — barcha xatolar logga yoziladi
- 🤖 Bot buyruqlari — `/start` va `/help` avtomatik ro'yxatdan o'tadi
- 💰 **BEPUL** — Gemini API ning bepul rejimi mavjud!

## 💰 Mijozlarga sotish
- Starter: $20/oy
- Pro: $50/oy
- Premium: $100/oy
