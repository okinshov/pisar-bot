import os
import logging
import asyncio
import re
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import aiohttp

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

FOOTER = "🤖 Генерує думки без вихідних."
LINKS = {
    "Python": "[Python](https://www.python.org/)",
    "Telegram": "[Telegram Bot API](https://core.telegram.org/bots/api)",
    "asyncio": "[asyncio](https://docs.python.org/3/library/asyncio.html)"
}

def format_steps(text: str) -> str:
    return re.sub(r'(?<!\d)\b(\d+)\. ', lambda m: f"{m.group(1)}️⃣ ", text)

def replace_keywords(text: str) -> str:
    if not isinstance(LINKS, dict):
        logger.error("LINKS має бути словником.")
        return text
    for word, link in LINKS.items():
        try:
            text = re.sub(rf"(?i)\b{re.escape(word)}\b", link, text)
        except Exception as e:
            logger.warning("Не вдалося замінити ключове слово %s: %s", word, e)
    return text

async def paraphrase_text(text: str) -> str:
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": f"Перефразуй: {text}"}]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    logger.error("OpenRouter %s: %s", resp.status, await resp.text())
                    return "⚠️ Помилка при зверненні до OpenRouter."
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", text)
    except Exception:
        logger.exception("Помилка під час перефразування")
        return "⚠️ Внутрішня помилка."

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_text = update.message.text
        if not user_text:
            await update.message.reply_text("🔹 Порожнє повідомлення.")
            return

        loading = await update.message.reply_text("⏳ Опрацьовую...")

        rewritten = await paraphrase_text(user_text)
        formatted = format_steps(rewritten)
        final_text = replace_keywords(formatted)

        await loading.edit_text(f"{final_text}\n\n{FOOTER}", parse_mode="Markdown")
    except Exception:
        logger.exception("Обробка повідомлення зірвалась")
        await update.message.reply_text("❌ Сталася помилка. Перевір журнал подій.")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("🚀 Бот готовий! Надішли текст для обробки.")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущено через polling.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
