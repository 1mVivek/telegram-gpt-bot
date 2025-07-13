import os, logging, asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai

load_dotenv()                       # loads variables from .env

TG_TOKEN       = os.getenv("TG_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if you like

openai.api_key = OPENAI_API_KEY

# ---------- model wrapper ---------- #
async def ask_gpt(prompt: str) -> str:
    resp = await openai.ChatCompletion.acreate(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

# ---------- Telegram handlers ---------- #
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m your GPT‑powered assistant.\n"
        "Send text to chat, *sum* to summarise, *tr* to translate, *write* to create.",
        parse_mode=ParseMode.MARKDOWN,
    )

async def helper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    low = prompt.lower()

    if low.startswith(("sum ", "summary ")):
        prompt = f"Summarise this in bullet points:\n{prompt.partition(' ')[2]}"
    elif low.startswith(("tr ", "translate ")):
        prompt = f"Translate this text accurately:\n{prompt.partition(' ')[2]}"
    elif low.startswith(("write ", "draft ")):
        prompt = f"Write creatively:\n{prompt.partition(' ')[2]}"

    reply = await ask_gpt(prompt)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TG_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, helper))

    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
