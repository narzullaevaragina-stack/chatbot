import os
import speech_recognition as sr
from dotenv import load_dotenv
from PIL import Image
import pytesseract
from pydub import AudioSegment
from gtts import gTTS

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
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

# Tesseract жолы
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ================= ТІЛДЕР =================
ALL_LANGUAGES = {
    "kk": "Қазақша 🇰🇿",
    "ru": "Русский 🇷🇺",
    "en": "English 🇬🇧",
    "tr": "Türkçe 🇹🇷",
    "de": "Deutsch 🇩🇪",
    "fr": "Français 🇫🇷",
}

# ================= КНОПКА =================
def get_language_keyboard():

    keyboard = []

    row = []

    for code, name in ALL_LANGUAGES.items():

        row.append(
            InlineKeyboardButton(
                name,
                callback_data=f"setlang_{code}"
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

# ================= АУДАРМА =================
async def process_translation(update, context, text):

    target_lang = context.user_data.get("lang")

    if not target_lang:

        await update.message.reply_text(
            "⚠️ Алдымен тілді таңдаңыз!",
            reply_markup=get_language_keyboard()
        )

        return

    try:

        translated = GoogleTranslator(
            source="auto",
            target=target_lang
        ).translate(text)

        # Мәтін шығару
        await update.message.reply_text(
            f"🌍 Аударма:\n{translated}"
        )

        # Voice жасау
        tts = gTTS(
            text=translated,
            lang=target_lang
        )

        voice_path = "voice.mp3"

        tts.save(voice_path)

        # Voice жіберу
        with open(voice_path, "rb") as audio:
            await update.message.reply_voice(audio)

        # Файл өшіру
        if os.path.exists(voice_path):
            os.remove(voice_path)

    except Exception as e:

        await update.message.reply_text(
            f"❌ Қате: {e}"
        )

# ================= TEXT / PHOTO =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # TEXT
    if update.message.text:

        await process_translation(
            update,
            context,
            update.message.text
        )

    # PHOTO
    elif update.message.photo or update.message.document:

        if update.message.document:

            mime_type = update.message.document.mime_type

            if not mime_type.startswith("image/"):

                await update.message.reply_text(
                    "❌ Бұл сурет емес."
                )

                return

            file = await update.message.document.get_file()

        else:
            file = await update.message.photo[-1].get_file()

        path = "temp.jpg"

        await file.download_to_drive(path)

        try:

            extracted_text = pytesseract.image_to_string(
                Image.open(path),
                lang="kaz+rus+eng"
            )

            if not extracted_text.strip():

                await update.message.reply_text(
                    "❌ Мәтін табылмады."
                )

            else:

                await update.message.reply_text(
                    f"🔍 Танылған мәтін:\n{extracted_text}"
                )

                await process_translation(
                    update,
                    context,
                    extracted_text
                )

        except Exception as e:

            await update.message.reply_text(
                f"❌ Қате: {e}"
            )

        finally:

            if os.path.exists(path):
                os.remove(path)

# ================= VOICE =================
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    voice = await update.message.voice.get_file()

    ogg_path = "voice.ogg"
    wav_path = "voice.wav"

    await voice.download_to_drive(ogg_path)

    try:

        # OGG -> WAV
        audio = AudioSegment.from_ogg(ogg_path)

        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()

        with sr.AudioFile(wav_path) as source:

            audio_data = recognizer.record(source)

            text = recognizer.recognize_google(audio_data)

        await update.message.reply_text(
            f"🎤 Танылған мәтін:\n{text}"
        )

        # Аудару
        await process_translation(
            update,
            context,
            text
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Voice қате: {e}"
        )

    finally:

        if os.path.exists(ogg_path):
            os.remove(ogg_path)

        if os.path.exists(wav_path):
            os.remove(wav_path)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🌍 Тілді таңдаңыз:",
        reply_markup=get_language_keyboard()
    )

# ================= CALLBACK =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data.startswith("setlang_"):

        lang = query.data.split("_")[1]

        context.user_data["lang"] = lang

        await query.edit_message_text(
            f"✅ Таңдалған тіл: {ALL_LANGUAGES[lang]}"
        )

# ================= MAIN =================
def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT |
            filters.PHOTO |
            filters.Document.IMAGE,
            handle_message
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            handle_voice
        )
    )

    print("🤖 AI Translator Bot іске қосылды...")

    app.run_polling()

# ================= RUN =================
if __name__ == "__main__":
    main()