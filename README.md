# 🤖 Super GPT Bot

Smart Telegram bot powered by OpenAI’s ChatGPT.  
Features: chat, summarise (`sum`), translate (`tr`), write creative text (`write`).

## Setup (Railway)

1. Fork this repo to Railway → New Project → Deploy from GitHub.
2. Add variables: `TG_TOKEN`, `OPENAI_API_KEY`, `OPENAI_MODEL`.
3. Start command: `python main.py`  
   Done! Your bot is live 24×7.

## Local test

```bash
pip install -r requirements.txt
cp .env.example .env  # fill with your keys
python main.py