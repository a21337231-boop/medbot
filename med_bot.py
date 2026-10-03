import os
import asyncio
import tempfile
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

CHAT_MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "whisper-large-v3"

SYSTEM_PROMPT = """Ты — умный помощник студента медицинского университета.
Отвечай на русском языке, чётко, структурированно и по делу.
Ты хорошо разбираешься в: анатомии, физиологии, патологической анатомии, фармакологии, биохимии, гистологии, микробиологии, патофизиологии и других медицинских предметах.
Если дают задание — решай его полностью с объяснением.
Если просят конспект — делай краткий, но информативный, с пунктами.
Всегда добавляй в конце: "⚠️ Проверяй информацию по учебникам и лекциям."
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой медицинский помощник 🩺\n\n"
        "Что я умею:\n"
        "• Отвечать на вопросы и задания по медицине\n"
        "• Превращать голосовые в текст\n"
        "• Делать краткие конспекты\n\n"
        "Просто напиши вопрос или пришли голосовое сообщение."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action("typing")

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Слушаю голосовое... ⏳")

    try:
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            audio_path = tmp.name

        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                language="ru"
            )
        text = transcript.text
        os.unlink(audio_path)

        await update.message.reply_text(f"📝 Текст:\n\n{text}")

        await update.message.chat.send_action("typing")
        summary = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\nСделай краткий структурированный конспект."},
                {"role": "user", "content": f"Сделай краткий конспект из этого текста:\n\n{text}"}
            ],
            temperature=0.2
        )
        await update.message.reply_text(f"📌 Краткий конспект:\n\n{summary.choices[0].message.content}")

    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке голосового: {e}")

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    print("Бот запущен!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
