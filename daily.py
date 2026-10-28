#!/usr/bin/env python3
"""Layoff Lottery daily card: pick today's meme/lesson/skill, post to Telegram, write docs/data."""
import html
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "docs" / "data"
FINAL = "final.json"
INDEX = "index.json"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
HTTP_TIMEOUT_S = 30

QUESTION_VI = "Sao hôm nay chưa phải ngày cuối?"
QUESTION_EN = "Why isn't today the end date?"
FINAL_VI = "🎉 Đến ngày cuối rồi. Bạn đã sống sót {n} ngày. Dù kết quả thế nào, xổ số kết thúc ở đây."
FINAL_EN = "🎉 End date reached. You survived {n} days. Whatever happened, the lottery ends here."


# ---- pure ----------------------------------------------------------------

def day_index(start, today):
    return (today - start).days + 1


def pick(items, day_n):
    if not items:
        raise ValueError("list is empty; add entries to the json file")
    return items[(day_n - 1) % len(items)]


def should_ask(date_str, chance):
    return random.Random(date_str).random() < chance


def phase(cfg, today, existing):
    start = date.fromisoformat(cfg["start_date"])
    end = cfg.get("end_date")
    if today < start:
        return "before"
    if end is None or today < date.fromisoformat(end):
        return "active"
    return "done" if FINAL in existing else "final"


def build_card(today, day_n, total_days, meme, lesson, skill, ask_question):
    return {
        "date": today.isoformat(), "day_n": day_n, "total_days": total_days,
        "meme": meme, "lesson": lesson, "skill": skill, "ask_question": ask_question,
    }


def counter(card, lang):
    n, m = card["day_n"], card["total_days"]
    label = "Ngày" if lang == "vi" else "Day"
    return f"{label} {n}/{m}" if m else f"{label} {n}"


def _block(card, lang):
    e = html.escape
    lines = [
        f"🎟 <b>{counter(card, lang)}</b> " + ("sống sót" if lang == "vi" else "survived"),
        f"📚 <b>{e(card['lesson']['topic'])}</b>: {e(card['lesson'][lang])}",
        f"🛠 <b>{e(card['skill']['name'])}</b>: {e(card['skill'][lang])}",
    ]
    if card["ask_question"]:
        lines.append("❓ " + (QUESTION_VI if lang == "vi" else QUESTION_EN))
    return "\n".join(lines)


def render_telegram(card):
    return _block(card, "vi") + "\n\n" + _block(card, "en")


# ---- io ------------------------------------------------------------------

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write_json(name, obj):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def telegram(token, method, **params):
    req = urllib.request.Request(
        TELEGRAM_API.format(token=token, method=method),
        data=urllib.parse.urlencode(params).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"telegram {method} failed: {err.code} {err.read().decode(errors='replace')}") from err
    if not body.get("ok"):
        raise RuntimeError(f"telegram {method} failed: {body}")


def dry_send(_token, method, **params):
    print(f"[dry-run] {method}:\n" + params.get("text", params.get("caption", "")) + "\n")


def send_card(send, token, chat_id, card):
    send(token, "sendPhoto", chat_id=chat_id, photo=card["meme"]["url"],
         caption=card["meme"]["vi"] + "\n" + card["meme"]["en"])
    send(token, "sendMessage", chat_id=chat_id, text=render_telegram(card), parse_mode="HTML")


def rebuild_index():
    days = sorted(p.stem for p in DATA.glob("????-??-??.json"))
    write_json(INDEX, days)


def main(argv):
    dry = "--dry-run" in argv
    cfg = load("docs/config.json")
    today = datetime.now(ZoneInfo(cfg["timezone"])).date()
    existing = {p.name for p in DATA.glob("*.json")} if DATA.exists() else set()
    ph = phase(cfg, today, existing)
    if ph in ("before", "done"):
        print(f"{today}: phase={ph}, nothing to do")
        return 0

    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not dry and not (token and chat_id):
        print("missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1
    send = dry_send if dry else telegram

    start = date.fromisoformat(cfg["start_date"])
    end = date.fromisoformat(cfg["end_date"]) if cfg.get("end_date") else None
    total = (end - start).days + 1 if end else None
    card_name = f"{today.isoformat()}.json"

    if ph == "active" or today == end:
        if card_name in existing:
            print(f"{today}: card already sent")
        else:
            day_n = day_index(start, today)
            card = build_card(
                today, day_n, total,
                pick(load("docs/memes.json"), day_n), pick(load("docs/lessons.json"), day_n), pick(load("docs/skills.json"), day_n),
                should_ask(today.isoformat(), cfg.get("question_chance", 0.3)),
            )
            if not dry:  # write first: a failed send must not cause a double-send on rerun
                write_json(card_name, card)
                rebuild_index()
            send_card(send, token, chat_id, card)
            print(f"{today}: card sent (day {day_n})")

    if ph == "final":
        if not dry:
            write_json(FINAL, {"sent": today.isoformat(), "total_days": total})
        send(token, "sendMessage", chat_id=chat_id,
             text=FINAL_VI.format(n=total) + "\n\n" + FINAL_EN.format(n=total))
        print(f"{today}: final message sent")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
