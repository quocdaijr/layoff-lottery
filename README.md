# Layoff Lottery

Every day still employed is a lottery ticket. A GitHub Action posts a daily card
(meme + one lesson + one skill nudge, vi + en) to Telegram and to a static page.

Setup:
1. Repo secrets: `TELEGRAM_BOT_TOKEN` (from @BotFather), `TELEGRAM_CHAT_ID` (your chat with the bot).
2. Settings → Pages → branch `main`, folder `/docs`.
3. Edit `docs/config.json` (dates), `docs/memes.json`, `docs/lessons.json`, `docs/skills.json`.

Local: `python -m unittest` · `python daily.py --dry-run`
