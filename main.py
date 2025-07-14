# main.py
import os, logging, asyncio
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
import openai

# ---------- config ----------
load_dotenv()                           # read .env when running locally

TG_TOKEN       = os.getenv("TG_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Render provides these automatically in production
PORT     = int(os.getenv("PORT", "10000"))
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")   # empty locally

assert TG_TOKEN and OPENAI_API_KEY, "❌ TG_TOKEN or OPENAI_API_KEY not set!"

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

# ---------- FastAPI + PTB ----------
app     = FastAPI()
bot_app = ApplicationBuilder().token(TG_TOKEN).build()

# ---------- GPT helper ----------
async def ask_gpt(prompt: str) -> str:
    """Call OpenAI ChatCompletion and return the assistant message text."""
    resp = await openai.ChatCompletion.acreate(
        model       = OPENAI_MODEL,
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = 1024,
        temperature = 0.7,
    )
    return resp.choices[0].message.content.strip()

# ---------- command / message handlers ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m your GPT assistant.\n"
        "Use **sum**, **tr**, or **write** before text—"
        "or the slash‑commands `/sum`, `/tr`, `/write`.",
        parse_mode=ParseMode.MARKDOWN,
    )

# plain‑text prefixes (sum …, tr …, write …)
async def helper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    low  = text.lower()

    if low.startswith(("sum ", "summary ")):
        prompt = f"Summarise this:\n{ text.partition(' ')[2] }"
    elif low.startswith(("tr ", "translate ")):
        prompt = f"Translate this text accurately:\n{ text.partition(' ')[2] }"
    elif low.startswith(("write ", "draft ")):
        prompt = f"Write creatively:\n{ text.partition(' ')[2] }"
    else:
        return                              # ignore anything else

    reply = await ask_gpt(prompt)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

# slash‑command helpers
async def cmd_sum(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(ctx.args)
    if not query:
        await update.message.reply_text("⚠️ Usage: /sum <text to summarise>")
        return
    reply = await ask_gpt(f"Summarise this:\n{query}")
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

async def cmd_tr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(ctx.args)
    if not query:
        await update.message.reply_text("⚠️ Usage: /tr <text to translate>")
        return
    reply = await ask_gpt(f"Translate this text accurately:\n{query}")
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

async def cmd_write(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(ctx.args)
    if not query:
        await update.message.reply_text("⚠️ Usage: /write <creative prompt>")
        return
    reply = await ask_gpt(f"Write creatively:\n{query}")
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

# ---------- register handlers ----------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("sum",   cmd_sum))
bot_app.add_handler(CommandHandler("tr",    cmd_tr))
bot_app.add_handler(CommandHandler("write", cmd_write))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, helper))

# ---------- webhook integration ----------
WEBHOOK_PATH = f"/telegram-webhook/{TG_TOKEN}"
WEBHOOK_URL  = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    """Forward Telegram updates (POSTed by Telegram) into python‑telegram‑bot."""
    data = await req.json()
    await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
    return {"ok": True}

# ---------- FastAPI lifecycle ----------
@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()

    if WEBHOOK_URL:            # production (public URL available)
        await bot_app.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=["message"])
        await bot_app.start()
        logging.info(f"✅ Webhook set → {WEBHOOK_URL}")
    else:                      # local dev fallback → long polling
        logging.info("🔄 No BASE_URL, falling back to long polling")
        asyncio.create_task(
            bot_app.run_polling(allowed_updates=["message"])
        )

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()