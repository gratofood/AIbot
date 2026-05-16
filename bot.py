import os
import time
import logging
from dotenv import load_dotenv
from groq import AsyncGroq
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# =============================================
# 📋 LOGGING — Xatolarni kuzatish tizimi
# =============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================
# ⚙️ SOZLAMALAR — .env fayldan o'qiladi
# =============================================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Tekshiruv — kalit kiritilmagan bo'lsa xato bersin
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    raise ValueError(
        "❌ TELEGRAM_TOKEN topilmadi!\n"
        "   .env faylga haqiqiy tokeningizni yozing.\n"
        "   Tokenni @BotFather dan olishingiz mumkin."
    )

if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
    raise ValueError(
        "❌ GROQ_API_KEY topilmadi!\n"
        "   .env faylga haqiqiy API kalitingizni yozing.\n"
        "   Kalitni console.groq.com dan olishingiz mumkin."
    )

# =============================================
# 🏪 BIZNES MA'LUMOTLARI — O'ZGARTIRING
# =============================================
BIZNES_NOMI = "Sarvinoy Go'zallik Saloni"
BIZNES_TELEFON = "+998 90 123 45 67"

BIZNES_MALUMOT = f"""Sen {BIZNES_NOMI} ning do'stona AI assistantisan.

Biznes haqida:
- Nomi: {BIZNES_NOMI}
- Manzil: Toshkent, Chilonzor tumani, 5-mavze
- Ish vaqti: Dushanba-Shanba, 09:00 - 20:00
- Telefon: {BIZNES_TELEFON}

Xizmatlar va narxlar:
- Soch kesish: 50,000 so'm
- Soch bo'yash: 150,000 so'mdan
- Manikur: 80,000 so'm
- Pedikur: 100,000 so'm
- Peshqadam (kelin): 500,000 so'm

Qoidalar:
1. Faqat shu biznes haqida gapir
2. O'zbek tilida javob ber
3. Qisqa va aniq javob ber (3-4 jumla)
4. Uchrashuv belgilash uchun telefonni ulash
5. Bilmasang: "Aniqroq ma'lumot uchun {BIZNES_TELEFON} ga qo'ng'iroq qiling" de
"""

# =============================================
# 🛡️ SPAM HIMOYASI — Rate Limiting
# =============================================
RATE_LIMIT_SECONDS = 3  # Har xabar orasida minimal vaqt
user_last_message = {}

# =============================================
# 🤖 GROQ (LLAMA-3) SOZLASH
# =============================================
groq_client = AsyncGroq(api_key=GROQ_API_KEY)


# Har bir foydalanuvchi uchun chat sessiyalarini saqlash
user_chats = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi /start yozganda"""
    nom = update.effective_user.first_name
    user_id = update.effective_user.id
    xabar = (
        f"Assalomu alaykum, {nom}! 👋\n\n"
        f"Men {BIZNES_NOMI} ning AI assistantiman.\n"
        f"Xizmatlar, narxlar yoki uchrashuv haqida savol bering!\n\n"
        f"Misol: 'Manikur narxi qancha?'"
    )
    # Yangi chat sessiyasini boshlash (suhbat tarixini tozalash)
    user_chats[user_id] = [{"role": "system", "content": BIZNES_MALUMOT}]
    await update.message.reply_text(xabar)


async def javob_ber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi xabar yozganda AI javob beradi"""
    user_id = update.effective_user.id
    savol = update.message.text

    # --- Spam tekshiruvi ---
    now = time.time()
    if user_id in user_last_message:
        elapsed = now - user_last_message[user_id]
        if elapsed < RATE_LIMIT_SECONDS:
            user_last_message[user_id] = now  # Spam davom etsa, vaqtni yana yangilaymiz
            await update.message.reply_text("⏳ Iltimos, xabarlar orasida biroz kuting...")
            return
    user_last_message[user_id] = now

    # --- Chat sessiyasini olish yoki yaratish ---
    if user_id not in user_chats:
        user_chats[user_id] = [{"role": "system", "content": BIZNES_MALUMOT}]

    chat_history = user_chats[user_id]
    chat_history.append({"role": "user", "content": savol})

    # Tarixni oxirgi 10 ta savol-javob bilan cheklash (Xotira to'lib ketmasligi uchun)
    if len(chat_history) > 21:
        chat_history = [chat_history[0]] + chat_history[-20:]

    # "Yozmoqda..." ko'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        max_retries = 3
        delay = 5
        javob = ""
        
        for attempt in range(max_retries):
            try:
                response = await groq_client.chat.completions.create(
                    messages=chat_history,
                    model="llama3-70b-8192",
                    temperature=0.7,
                    max_tokens=500
                )
                javob = response.choices[0].message.content
                chat_history.append({"role": "assistant", "content": javob})
                break
            except Exception as e:
                error_msg = str(e).lower()
                # 429 yoki rate limit xatolarida kutamiz
                if attempt < max_retries - 1 and ("quota" in error_msg or "rate" in error_msg or "resource" in error_msg or "503" in error_msg or "traffic" in error_msg):
                    logger.warning(f"⚠️ API band, {delay} soniya kutilmoqda (Urinish: {attempt+1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise e

        logger.info(f"Foydalanuvchi [{user_id}]: {savol[:50]}...")

    except Exception as e:
        error_msg = str(e).lower()

        if "api_key" in error_msg or "authentication" in error_msg or "permission" in error_msg:
            logger.error("❌ Groq API kalit noto'g'ri!")
            javob = "Uzr, tizim sozlamalarida xato bor. Iltimos keyinroq qaytadan urinib ko'ring."

        elif "quota" in error_msg or "rate" in error_msg:
            logger.warning("⚠️ Groq API limit ga yetdi")
            javob = "Hozir juda ko'p so'rov bor. Iltimos 1 daqiqadan so'ng qaytadan yozing."

        elif "connection" in error_msg or "timeout" in error_msg:
            logger.error("❌ Groq API ga ulanib bo'lmadi (internet muammosi)")
            javob = f"Uzr, hozir internet bilan muammo bor. Iltimos {BIZNES_TELEFON} ga qo'ng'iroq qiling."

        else:
            logger.error(f"Kutilmagan xato: {e}", exc_info=True)
            javob = f"Uzr, hozir texnik nosozlik bor. Iltimos {BIZNES_TELEFON} ga qo'ng'iroq qiling."
            # Agar xato bo'lsa, oxirgi savolni tarixdan olib tashlaymiz
            chat_history.pop()

    await update.message.reply_text(javob)


async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help buyrug'i"""
    xabar = (
        "📋 Nima so'rashingiz mumkin:\n\n"
        "• Xizmatlar ro'yxati\n"
        "• Narxlar\n"
        "• Ish vaqti\n"
        "• Manzil\n"
        "• Uchrashuv belgilash\n\n"
        "Shunchaki yozing, javob beraman! 😊"
    )
    await update.message.reply_text(xabar)


async def post_init(application):
    """Bot ishga tushganda buyruqlarni ro'yxatdan o'tkazish"""
    await application.bot.set_my_commands([
        BotCommand("start", "Botni boshlash"),
        BotCommand("help", "Yordam"),
    ])
    logger.info("✅ Bot buyruqlari ro'yxatdan o'tkazildi")


# =============================================
# 🌐 RENDER UCHUN DUMMY SERVER (Port xatosi bermasligi uchun)
# =============================================
def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
        def log_message(self, format, *args):
            pass
            
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# =============================================
# 🚀 BOTNI ISHGA TUSHIRISH
# =============================================
def main():
    logger.info(f"🚀 {BIZNES_NOMI} boti ishga tushmoqda...")

    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", yordam))

    # Barcha matnli xabarlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, javob_ber))

    logger.info(f"✅ {BIZNES_NOMI} boti muvaffaqiyatli ishga tushdi!")

    # Boshlash
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
