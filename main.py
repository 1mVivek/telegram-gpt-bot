import os, logging, asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes
)
import openai
from fastapi import FastAPI, Request

load_dotenv()

TG_TOKEN       = os.getenv("TG_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT           = int(os.getenv("PORT", "10000"))          # Render sets PORT
BASE_URL       = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")  # auto‑filled by Render

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

app = FastAPI()                   # FastAPI instance for Render

# ---------- PTB application ---------- #
bot_app = ApplicationBuilder().token(TG_TOKEN).build()

async def ask_gpt(prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m your GPT assistant.\n"
        "Use `sum`, `tr`, or `write` before text.",
        parse_mode=ParseMode.MARKDOWN,
    )

async def helper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    low  = text.lower()
    if low.startswith(("sum ", "summary ")):
        text = f"Summarise this:\n{ text.partition(' ')[2] }"
    elif low.startswith(("tr ", "translate ")):
        text = f"Translate this text accurately:\n{ text.partition(' ')[2] }"
    elif low.startswith(("write ", "draft ")):
        text = f"Write creatively:\n{ text.partition(' ')[2] }"

    reply = await ask_gpt(text)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, helper))

# ---------- Webhook setup ---------- #
WEBHOOK_PATH = f"/telegram-webhook/{TG_TOKEN}"
WEBHOOK_URL  = f"{BASE_URL}{WEBHOOK_PATH}"

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    """Forward Telegram updates to PTB."""
    data = await req.json()
    await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
    return {"ok": True}

async def on_startup():
    # Set webhook
    await bot_app.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=["message"])
    logging.info("Webhook set to %s", WEBHOOK_URL)

# PTB runs inside same event loop FastAPI uses
asyncio.get_event_loop().create_task(bot_app.initialize())
asyncio.get_event_loop().create_task(on_startup())
asyncio.get_event_loop().create_task(bot_app.start())

# ---------- Run with Uvicorn ---------- #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)