import os
import logging
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import aiohttp
import nest_asyncio

# Логування
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Інтеграція з нестабільними циклами (Render, Replit тощо)
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

def log_status(message: str):
    logger.info(f"[СТАТУС] {message}")

def log_error(error: str):
    logger.error(f"[ПОМИЛКА] {error}")

FOOTER = "..."

LINKS = { ... }  # Залиш як є

def format_steps(text: str) -> str:
    return re.sub(r'(?<!\d)\b(\d+)\. ', lambda m: f"{m.group(1)}️⃣ ", text)

def replace_keywords(text: str) -> str:
    for word, link in LINKS.items():
        text = re.sub(rf"(?i)\b{re.escape(word)}\b", link, text)
    return text

async def paraphrase_text(text: str) -> str:
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
        data = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": f"... {text}"}]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    log_error(f"OpenRouter API error — статус {response.status}")
                    return "⚠️ Помилка при зверненні до OpenRouter API."
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", text)
    except Exception as e:
        log_error(f"Не вдалося переписати текст: {e}")
        return "⚠️ Сталася внутрішня помилка при обробці тексту."

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_text = update.message.text
        log_status(f"Отримано повідомлення: {user_text[:50]}")

        if not user_text:
            await update.message.reply_text("🔹 Повідомлення порожнє.")
            return

        loading_msg = await update.message.reply_text("⏳ Обробляю ваш текст...")

        rewritten = await paraphrase_text(user_text)
        formatted = format_steps(rewritten)
        final_text = replace_keywords(formatted)

        await loading_msg.edit_text(f"{final_text}\n\n{FOOTER}", parse_mode="Markdown")
        log_status("Відповідь відправлено успішно.")
    except Exception as e:
        log_error(f"Помилка обробки повідомлення: {e}")
        await update.message.reply_text("❌ Виникла помилка. Спробуйте знову.")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("🚀 Надішли мені текст, і я його покращу!")

async def main():
    try:
        log_status("Запуск додатку")
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        log_status("Бот запущено, очікую повідомлення.")
        await app.run_polling()
    except Exception as e:
        log_error(f"Фатальна помилка при запуску: {e}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

