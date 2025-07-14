# main.py
import os, logging, asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai

load_dotenv()
logging.basicConfig(level=logging.INFO)

TG_TOKEN = os.getenv("TG_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "10000"))

assert TG_TOKEN and OPENAI_API_KEY, "❌ TG_TOKEN or OPENAI_API_KEY missing!"

openai.api_key = OPENAI_API_KEY

app = FastAPI()
bot_app = ApplicationBuilder().token(TG_TOKEN).build()

# ---------- helpers ----------
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
        parse_mode="Markdown",
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
    await update.message.reply_text(reply, parse_mode="Markdown")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, helper))

# ---------- webhook ----------
WEBHOOK_PATH = f"/telegram-webhook/{TG_TOKEN}"
WEBHOOK_URL  = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()

    if WEBHOOK_URL:                      # production on Render
        await bot_app.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=["message"])
        logging.info(f"Webhook set to {WEBHOOK_URL}")
        await bot_app.start()
    else:                                # local dev, no public URL
        logging.info("No BASE_URL → starting long‑polling")
        asyncio.create_task(bot_app.run_polling(allowed_updates=["message"]))

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()