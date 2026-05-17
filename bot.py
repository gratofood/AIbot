import os
import time
import logging
from dotenv import load_dotenv
from groq import AsyncGroq
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
from flask import Flask

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
BIZNES_NOMI = "Grato"
BIZNES_TELEFON = "+998 99 736 36 36"

BIZNES_MALUMOT = f"""Sen {BIZNES_NOMI} shirinliklar do'konining do'stona AI assistantisan.

Biznes haqida:
- Nomi: {BIZNES_NOMI}
- Filiallar: 5-mkr, Kalxoz bozori, Gala Osiyo, Sharq, Guliver
- Ish vaqti: Har kuni, 08:00 - 23:00
- Telefon: {BIZNES_TELEFON}
- Yetkazib berish: Bor (pullik)

Mahsulotlar:
- Tortlar (buyurtmaga va tayyor)
- Pirojnoelar (turli xil)
- Yarimtayyor mahsulotlar

Qoidalar:
1. Faqat shu biznes haqida gapir
2. O'zbek tilida javob ber
3. Qisqa va aniq javob ber (3-4 jumla)
4. Buyurtma berish yoki savollar uchun telefonni ulash
5. Bilmasang: "Aniqroq ma'lumot uchun {BIZNES_TELEFON} ga qo'ng'iroq qiling" de
6. Mijozlarga iliq va samimiy munosabatda bo'l
7. Agar narx so'rasa, aniq narxni bilmasang "Narxlar turga qarab farq qiladi, {BIZNES_TELEFON} ga qo'ng'iroq qilib aniqlashtiring" de
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
        f"Assalomu alaykum, {nom}! 🍰\n\n"
        f"Men {BIZNES_NOMI} shirinliklar do'konining AI assistantiman.\n"
        f"Tortlar, pirojnoelar, yetkazib berish yoki filiallarimiz haqida savol bering!\n\n"
        f"Misol: 'Tort buyurtma qilsam bo'ladimi?'"
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
                    model="llama-3.3-70b-versatile",
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
        "🍰 Tortlar va pirojnoelar\n"
        "📦 Yarimtayyor mahsulotlar\n"
        "🚗 Yetkazib berish\n"
        "📍 Filiallar manzili\n"
        "🕐 Ish vaqti\n"
        "📞 Buyurtma berish\n\n"
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
# 🚀 BOTNI ISHGA TUSHIRISH (Render uchun moslashtirilgan)
# =============================================
def main():
    logger.info(f"🚀 {BIZNES_NOMI} boti ishga tushmoqda...")

    # 1. Telegram botni orqa fonda (yashirin) ishga tushiramiz
    def run_bot_in_background():
        app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

        # Buyruqlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", yordam))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, javob_ber))

        logger.info(f"✅ {BIZNES_NOMI} boti muvaffaqiyatli ishga tushdi!")
        
        # Asyncio tsiklini yaratamiz
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # stop_signals=() juda muhim! Busiz orqa fonda ishlamaydi
        app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=())

    bot_thread = threading.Thread(target=run_bot_in_background, daemon=True)
    bot_thread.start()

    # 2. Flask veb-serverini asosiy (asosiy) jarayon sifatida ishga tushiramiz
    # Shunda Render "Ha bu aniq veb-sayt ekan" deb darhol qabul qiladi!
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    web_app = Flask(__name__)
    
    @web_app.route('/')
    def index():
        return "Bot 24/7 ishlash rejimida yoniq!"
        
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)



if __name__ == "__main__":
    main()
