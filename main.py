import os
import logging
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import aiohttp

# Логування
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Токени з Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

FOOTER = """
[Біржі](https://t.me/zarahovano/2738) • [Проксі](https://stableproxy.com/?r=OWCN20XR) • [Ютуб](https://www.youtube.com/channel/UCCTNQRN8dr-YuLL-GEYPdcw) • [Чат](https://t.me/+w2SAKBpzFDhhYTMy) • [Карта](https://t.me/zarahovano/3724)
"""

LINKS = {
    "Binance": "[Binance](https://accounts.binance.com/uk-UA/register?ref=GKWWK7SB)",
    "ByBit": "[ByBit](https://partner.bybit.com/b/zarahovano)",
    "WhiteBIT": "[WhiteBit](https://whitebit.com/referral/bcb23ae8-a01a-455c-b104-b2728711d712)",
    "OKX": "[OKX](https://www.okx.com/join/7045895)",
    "MEXC": "[MEXC](https://m.mexc.com/auth/signup?inviteCode=1RSm3)",
    "Phemex": "[Phemex](https://phemex.com/register-vt1?referralCode=EB95B5)",
    "Bitget": "[Bitget](https://www.bitget.com/ru/referral/register?clacCode=XQU9UEFN)"
}

def format_steps(text: str) -> str:
    return re.sub(r'(?<!\d)\b(\d+)\. ', lambda m: f"{m.group(1)}️⃣ ", text)

def replace_keywords(text: str) -> str:
    for word, link in LINKS.items():
        text = re.sub(rf"(?i)\b{re.escape(word)}\b", link, text)
    return text

async def paraphrase_text(text: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{
            "role": "user",
            "content": f"Перепиши цей телеграм-пост у крипто-стилі... Мова посту українська... Якщо в оригінальному пості є нумерований список збережи його... Назва нумерованого посту Що робити... Оригінальний пост: {text}"
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            response_text = await response.text()
            if response.status != 200:
                logger.warning(f"OpenRouter error response ({response.status}): {response_text}")
                return "⚠️ Виникла проблема з обробкою тексту."
            try:
                result = await response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    logger.warning(f"OpenRouter пустий контент: {response_text}")
                    return "⚠️ OpenRouter не надіслав відповідь."
                return content
            except Exception as e:
                logger.error(f"Не вдалося розібрати JSON: {e} | Тіло відповіді: {response_text}")
                return "⚠️ Виникла помилка при обробці відповіді від OpenRouter."

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    if not user_text:
        await update.message.reply_text("🔹 Немає тексту для обробки.")
        return

    loading_msg = await update.message.reply_text("⏳ Обробляю текст...")

    try:
        rewritten = await paraphrase_text(user_text)
        formatted = format_steps(rewritten)
        final = replace_keywords(formatted)
        await loading_msg.edit_text(f"{final}\n\n{FOOTER}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Помилка: {e}")
        await loading_msg.edit_text("⚠️ Щось пішло не так.")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("🚀 Надішли мені текст, і я його покращу!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущено!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(main())
    loop.run_forever()

