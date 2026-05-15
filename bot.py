import sys
import os

# Жүйеге қажетті кітапханаларды және папка бағыттарын дұрыс көрсету
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import speech_recognition as sr
from dotenv import load_dotenv
from pydub import AudioSegment
from gtts import gTTS
from threading import Thread
from flask import Flask

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from deep_translator import GoogleTranslator

# ================= CONFIG =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ================= FLASK SERVER (RENDER) =================
app = Flask('')

@app.route('/')
def home():
    return "Бот сәтті іске қосылды!"

def run_flask():
    # Render талап ететін портты міндетті түрде тексеру және байланыстыру
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True  # Негізгі процесс тоқтағанда Flask-ты да таза жабу үшін
    t.start()

# ================= ТІЛДЕР =================
ALL_LANGUAGES = {
    "kk": "Қазақша 🇰🇿",
    "ru": "Русский 🇷🇺",
    "en": "English 🇬🇧",
    "tr": "Türkçe 🇹🇷",
    "de": "Deutsch 🇩🇪",
    "fr": "Français 🇫🇷",
    "ja": "Жапония 🇯🇵",
    "ko": "Корея 🇰🇷",
}

def get_language_keyboard():
    keyboard = [
        [InlineKeyboardButton("Қазақша 🇰🇿", callback_data="setlang_kk"), InlineKeyboardButton("Русский 🇷🇺", callback_data="setlang_ru")],
        [InlineKeyboardButton("English 🇬🇧", callback_data="setlang_en"), InlineKeyboardButton("Türkçe 🇹🇷", callback_data="setlang_tr")],
        [InlineKeyboardButton("Deutsch 🇩🇪", callback_data="setlang_de"), InlineKeyboardButton("Français 🇫🇷", callback_data="setlang_fr")],
        [InlineKeyboardButton("Жапония 🇯🇵", callback_data="setlang_ja"), InlineKeyboardButton("Корея 🇰🇷", callback_data="setlang_ko")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= АУДАРМА =================
async def process_translation(update, context, text):
    target_lang = context.user_data.get("lang")
    if not target_lang:
        await update.message.reply_text("⚠️ Алдымен тілді таңдаңыз!", reply_markup=get_language_keyboard())
        return

    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        await update.message.reply_text("🌍 Аударма:\n" + str(translated))

        tts = gTTS(text=translated, lang=target_lang)
        voice_path = "voice.mp3"
        tts.save(voice_path)
        
        with open(voice_path, "rb") as audio:
            await update.message.reply_voice(audio)
        if os.path.exists(voice_path): os.remove(voice_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Қате: {e}")

# ================= МӘТІНДІ ӨҢДЕУ (СУРЕТСІЗ) =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        await process_translation(update, context, update.message.text)
    elif update.message.photo or update.message.document:
        await update.message.reply_text("⚠️ Кешіріңіз, суретті оқу функциясы өшірілген. Тек мәтін немесе дауыстық хабарлама жіберіңіз.")

# ================= VOICE =================
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = await update.message.voice.get_file()
    ogg_path, wav_path = "voice.ogg", "voice.wav"
    await voice.download_to_drive(ogg_path)

    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            text = recognizer.recognize_google(recognizer.record(source))
        await update.message.reply_text(f"🎤 Танылған мәтін:\n{text}")
        await process_translation(update, context, text)
    except Exception as e:
        await update.message.reply_text(f"❌ Voice қате: {e}")
    finally:
        for p in [ogg_path, wav_path]:
            if os.path.exists(p): os.remove(p)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Сәлем! Тілді таңдаңыз:", reply_markup=get_language_keyboard())

async def post_init(application: Application) -> None:
    commands = [BotCommand("start", "Бастау"), BotCommand("language", "Тілді өзгерту")]
    await application.bot.set_my_commands(commands)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("setlang_"):
        lang = query.data.split("_")[1]
        context.user_data["lang"] = lang
        await query.edit_message_text(f"✅ Тіл орнатылды: {ALL_LANGUAGES[lang]}")

def main():
    if not TOKEN: 
        print("ҚАТЕ: BOT_TOKEN табылмады. Environment variables тексеріңіз.")
        return
        
    app_tg = Application.builder().token(TOKEN).post_init(post_init).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("language", start))
    app_tg.add_handler(CallbackQueryHandler(callback_handler))
    app_tg.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.IMAGE, handle_message))
    app_tg.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Алдымен Flask серверін фондық режимде қосамыз
    keep_alive()
    
    # Содан кейін Telegram лонг-поллингті іске қосамыз
    app_tg.run_polling()

if __name__ == "__main__":
    main()
