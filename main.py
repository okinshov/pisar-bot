import os
import logging
import asyncio
import re
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import aiohttp
import nest_asyncio

# Ініціалізація логів
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

FOOTER = "🤖 Створено ботом-помічником. Зворотний зв'язок — завжди вітається!"

# Оновлений словник ключових слів
LINKS = {
    "Python": "[Python](https://www.python.org/)",
    "asyncio": "[asyncio](https://docs.python.org/3/library/asyncio.html)",
    "telegram": "[Telegram Bot API](https://core.telegram.org/bots/api)",
    "aiohttp": "[aiohttp](https://docs.aiohttp.org/)",
    # Додай інші ключові слова за потреби
}

def format_steps(text: str) -> str:
    return re.sub(r'(?<!\d)\b(\d+)\. ', lambda m: f"{m.group(1)}️⃣ ", text)

def replace_keywords(text: str) -> str:
    if not isinstance(LINKS, dict):
        logger.error("❗ LINKS повинен бути словником, а не типу %s", type(LINKS).__name__)
        return text
    for word, link in LINKS.items():
        try:
            text = re.sub(rf"(?i)\b{re.escape(word)}\b", link, text)
        except Exception as e:
            logger.warning("⚠️ Не вдалося замінити слово '%s': %s", word, e)
    return text

async def paraphrase_text(text: str) -> str:
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
        data = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [{
                "role": "user",
                "content": f"Перефразуй наступний текст, зберігаючи зміст: {text}"
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ OpenRouter помилка {response.status}: {error_text}")
                    return "⚠️ Помилка при зверненні до OpenRouter."
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", text)
    except Exception as e:
        logger.exception("‼️ Парaфразування провалено")
        return "⚠️ Внутрішня помилка. Спробуйте ще раз."

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_text = update.message.text
        if not user_text:
            await update.message.reply_text("🔹 Порожнє повідомлення.")
            return

        loading_msg = await update.message.reply_text("⏳ Опрацьовую...")

        rewritten = await paraphrase_text(user_text)
        formatted = format_steps(rewritten)
        final_text = replace_keywords(formatted)

        await loading_msg.edit_text(f"{final_text}\n\n{FOOTER}", parse_mode="Markdown")
    except Exception as e:
        logger.exception("🚨 Обробка зірвалась")
        await update.message.reply_text("❌ Сталася помилка. Перевір логи або спробуй пізніше.")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("🚀 Я готовий обробляти тексти! Надішли мені повідомлення 📩")

async def reset_webhook():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook()
    logger.info("✅ Webhook очищено")

async def main():
    await reset_webhook()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Бот запущено через polling.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
