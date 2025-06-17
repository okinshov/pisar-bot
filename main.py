import os
import logging
import asyncio
import nest_asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import aiohttp

# Виправлення сумісності з Replit
nest_asyncio.apply()

# Налаштування логування
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Читання API токенів
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

# Футер для повідомлень
FOOTER = """
[Біржі](https://t.me/zarahovano/2738) • [HOT](https://t.me/herewalletbot/app?startapp=151723-village-27582) • [Проксі](https://stableproxy.com/?r=OWCN20XR) • [Ютуб](https://www.youtube.com/channel/UCCTNQRN8dr-YuLL-GEYPdcw) • [Чат](https://t.me/+w2SAKBpzFDhhYTMy) • [Карта](https://t.me/zarahovano/3724)
"""

# Ключові слова для заміни на Markdown-гіперпосилання
LINKS = {
    "Binance": "[Binance](https://accounts.binance.com/uk-UA/register?ref=GKWWK7SB)",
    "ByBit": "[ByBit](https://partner.bybit.com/b/zarahovano)",
    "WhiteBit": "[WhiteBit](https://whitebit.com/referral/bcb23ae8-a01a-455c-b104-b2728711d712)",
    "OKX": "[OKX](https://www.okx.com/join/7045895)",
    "MEXC": "[MEXC](https://m.mexc.com/auth/signup?inviteCode=1RSm3)",
    "Phemex": "[Phemex](https://phemex.com/register-vt1?referralCode=EB95B5)",
}

def format_steps(text: str) -> str:
    """Додає емодзі 1️⃣, 2️⃣, 3️⃣ перед кроками у тексті"""
    step_pattern = re.compile(r'(?<!\d)\b(\d+)\. ')
    return step_pattern.sub(lambda m: f"{m.group(1)}️⃣ ", text)

def replace_keywords(text: str) -> str:
    """Автоматично замінює ключові слова на Markdown-гіперпосилання після перефразування"""
    for word, link in LINKS.items():
        text = re.sub(rf"(?i)\b{re.escape(word)}\b", link, text)  
    return text

async def paraphrase_text(text: str) -> str:
    """Переписує текст, щоб він звучав привабливо та зрозуміло"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": f"Перепиши цей текст так, щоб він був цікавим для новачків: {text}"}]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                return "⚠️ Виникла проблема з обробкою тексту. Спробуйте ще раз."
            
            result = await response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", text)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обробляє текстові повідомлення, спочатку переписує, додає марковані кроки та посилання"""
    user_text = update.message.text

    if not user_text:
        await update.message.reply_text("🔹 Повідомлення не містить тексту або його неможливо обробити.")
        return

    loading_message = await update.message.reply_text("⏳ Формую оновлений текст... Зачекайте!")

    try:
        paraphrased_text = await paraphrase_text(user_text)
        formatted_text = format_steps(paraphrased_text)
        final_text = replace_keywords(formatted_text)

        await loading_message.edit_text(f"{final_text}\n\n{FOOTER}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Помилка: {e}")
        await loading_message.edit_text("⚠️ Виникла проблема з обробкою тексту. Спробуйте ще раз.")

async def start(update: Update, context: CallbackContext) -> None:
    """Привітальне повідомлення"""
    await update.message.reply_text("🚀 Надішли мені текст, і я його покращу!")

async def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущено!")
    await app.initialize()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
