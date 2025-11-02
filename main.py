
def _looks_like_username(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("@") or s.lower().startswith("t.me/") or s.lower().startswith("https://t.me/"))

async def parse_target_id(client: Client, ch_text: str, fallback_id: int) -> int:
    """
    Accepts -100..., numeric, @username, or t.me/<name> and returns numeric id.
    """
    try:
        if not ch_text or ch_text.strip() in ("/d", "/D"):
            return fallback_id
        s = ch_text.strip()
        if _looks_like_username(s):
            uname = s.replace("https://t.me/", "").replace("t.me/", "").lstrip("@").split("/")[0]
            chat = await client.get_chat(uname)
            return chat.id
        # numeric
        return int(s)
    except Exception:
        return fallback_id

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patched main.py
- Topic extraction from bracketed text (e.g., (Arithmetic))
- Captions show Topic (separate section) -> File -> Batch
- Topic-wise clickable index built AFTER saving to DB/JSON
- /drm works in private, groups, channels (bot must be admin in groups/channels)
- Stores index to Mongo via your existing db module (if functions available) AND to JSON
- Keeps your helpers (ug helper, utils, vars) intact
"""

import os, re, sys, json, time, asyncio, random
import requests, aiohttp
from collections import defaultdict
from datetime import datetime
from pyrogram import Client, filters, idle
from pyromod import listen
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChatAdminRequired
from pyrogram.handlers import MessageHandler

# Your modules (expected to exist in repo)
from vars import *     # API_ID, API_HASH, BOT_TOKEN, OWNER_ID, CREDIT, etc.
from db import db      # must be Mongo-backed per your setup
import ug as helper    # your downloader helpers
from clean import register_clean_handler
from jbebwnqnwewwjn import get_apis

apis = get_apis()

# ------------------ Utilities ------------------
def extract_topic(title: str) -> str:
    m = re.search(r"\(([^)]+)\)", title or "")
    return m.group(1).strip() if m else "General"

async def build_message_link(bot: Client, chat_id: int, message_id: int) -> str:
    try:
        chat = await bot.get_chat(chat_id)
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{message_id}"
        cid = str(chat_id)
        if cid.startswith("-100"):
            return f"https://t.me/c/{cid[4:]}/{message_id}"
        return f"https://t.me/c/{abs(chat_id)}/{message_id}"
    except Exception:
        cid = str(chat_id)
        if cid.startswith("-100"):
            return f"https://t.me/c/{cid[4:]}/{message_id}"
        return f"https://t.me/c/{abs(chat_id)}/{message_id}"

def persist_topic_index_json(batch_name: str, topic_index: dict) -> typing.Optional[str]:
    safe = re.sub(r"[^\w\-_. ]", "_", batch_name or "batch")[:60]
    fname = f"topic_index_{safe}.json"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(topic_index, f, ensure_ascii=False, indent=2)
        return fname
    except Exception as e:
        print("persist_topic_index_json error:", e)
        return None

def try_db_save_index(batch_name: str, topic_index: dict):
    try:
        if hasattr(db, "set_topic_index"):
            db.set_topic_index(batch_name, topic_index)
        elif hasattr(db, "save_topic_index"):
            db.save_topic_index(batch_name, topic_index)
    except Exception as e:
        print("DB index save failed:", e)

def sanitize_filename(name: str, limit: int = 60) -> str:

# --- Forum Topic Helpers (auto topic create & use) ---
async def get_or_create_forum_topic(bot: Client, chat_id: int, title: str) -> typing.Optional[int]:
    """
    Create or fetch a forum topic in a supergroup with topics enabled.
    Returns the message_thread_id usable in send_* calls.
    """
    try:
        chat = await bot.get_chat(chat_id)
        if not getattr(chat, "is_forum", False):
            return None
        topic = await bot.create_forum_topic(chat_id, title[:128] if title else "Topic")
        return getattr(topic, "message_thread_id", None)
    except Exception as e:
        try:
            topic = await bot.create_forum_topic(chat_id, "Auto Index")
            return getattr(topic, "message_thread_id", None)
        except Exception:
            return None
    cleaned = re.sub(r"[^\w\s\-\.,]", " ", name or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:limit] if limit else cleaned

# ------------------ Bot Init ------------------
bot = Client("ug", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
register_clean_handler(bot)

photologo = 'https://cdn.pixabay.com/photo/2025/05/21/02/38/ai-generated-9612673_1280.jpg'
BUTTONSCONTACT = InlineKeyboardMarkup([[InlineKeyboardButton(text="📞 Contact", url="https://t.me/TgXWarriors")]])

# ------------------ /start ------------------
@bot.on_message(filters.command("start") & (filters.private | filters.group | filters.channel))
async def start_cmd(client: Client, m: Message):
    try:
        if m.chat.type == "private":
            is_authorized = db.is_user_authorized(m.from_user.id, client.me.username)
            if not is_authorized:
                await m.reply_photo(
                    photo=photologo,
                    caption="**🔒 Access Required**\n\nContact admin to get access.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💫 Get Access", url="https://t.me/TgXWarriors")]
                    ])
                )
                return
        await m.reply_text("Hello! Bot is running...")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await m.reply_text("Hello! Bot is running...")

# ------------------ /drm ------------------
@bot.on_message(filters.command(["drm"]) & (filters.private | filters.group | filters.channel))
async def drm_handler(client: Client, m: Message):
    # ### DRM_MAIN_TRY
    try:
    """
    Flow:
    1) Accept text file with lines "Name ... : https://..."
    2) Extract topic from (Topic) in name string
    3) Ask batch/resolution/credit/thumb/target chat like your original flow
    4) For each item: send file with caption containing Topic section (first), then File, then Batch
    5) For each sent message: create permalink, store in topic_index (memory) and persist to DB + JSON (first, then post index)
    6) Works in private, groups, channels (if bot is admin in non-private)
    """
    bot_info = await client.get_me()
    bot_username = bot_info.username

    # Permissions for groups/channels
    if m.chat.type in ("supergroup", "group", "channel"):
        try:
            me_member = await client.get_chat_member(m.chat.id, bot_info.id)
            if not (me_member.status in ("administrator", "creator")):
                await m.reply_text("🔒 Make me admin to run /drm here.")
                return
        except Exception:
            await m.reply_text("🔒 I need admin rights here to run /drm.")
            return
    else:
        if not db.is_user_authorized(m.from_user.id, bot_username):
            await m.reply_photo(
                photo=photologo,
                caption="**🔒 Access Required**\n\nContact admin to get access.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💫 Get Access", url="https://t.me/TgXWarriors")]])
            )
            return

    editable = await m.reply_text(
        "__Hii, I am DRM Downloader Bot__\n"
        "<blockquote><i>Send me a .txt file containing entries like:\n"
        "Name (Topic) : https://example.com/file\n</i></blockquote>\n"
        "<blockquote><i>All input auto taken in 20 sec\nPlease send all input in 20 sec...\n</i></blockquote>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 Join Premium Group", url="https://t.me/TgXWarriors")]])
    )
    input_msg: Message = await client.listen(editable.chat.id)

    # Forum detection & topic threads map
    try:
        chat_info = await client.get_chat(m.chat.id)
        is_forum = bool(getattr(chat_info, 'is_forum', False))
    except Exception:
        is_forum = False
    topic_threads = {}  # {topic: thread_id}

    if not input_msg.document or not input_msg.document.file_name.endswith(".txt"):
        await m.reply_text("❌ Please send a .txt file!")
        return

    x_path = await input_msg.download()
    await client.send_document(OWNER_ID, x_path)
    await input_msg.delete(True)

    # Parse lines into [(name, url)]
    links = []
    with open(x_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            murl = re.search(r"(https?://\S+)", line)
            if not murl:
                continue
            url = murl.group(1)
            name_part = line.split(url, 1)[0].strip().rstrip(":|")
            if not name_part:
                name_part = url
            links.append([name_part, url])

    if not links:
        await editable.edit("❌ No valid links found in your file.")
        return

    # Summarize
    await editable.edit(f"**Found {len(links)} links.**\nSend start index (default 1).")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        start_idx = int(ans.text.strip())
        await ans.delete(True)
    except Exception:
        start_idx = 1

    await editable.edit("**Enter Batch Name or send /d**")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        b_name = ans.text.strip()
        await ans.delete(True)
    except Exception:
        b_name = "/d"
    if b_name == "/d":
        b_name = os.path.splitext(os.path.basename(x_path))[0].replace("_", " ")

    await editable.edit("__**Enter resolution or Video Quality (`144`, `240`, `360`, `480`, `720`, `1080`)**__")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        res_text = ans.text.strip()
        await ans.delete(True)
    except Exception:
        res_text = "480"

    await editable.edit("**Enter watermark text or send /d**")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        wm = ans.text.strip()
        await ans.delete(True)
    except Exception:
        wm = "/d"
    watermark = "Mrs.UC" if wm == "/d" else wm

    await editable.edit("__**Enter Credit Name or send /d**__")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        credit = ans.text.strip()
        await ans.delete(True)
    except Exception:
        credit = "/d"
    CR = f"{CREDIT}" if credit == "/d" else credit

    await editable.edit("__**Provide the Channel ID or send /d (use current chat)**__")
    try:
        ans = await client.listen(editable.chat.id, timeout=20)
        ch_text = ans.text.strip()
        await ans.delete(True)
    except Exception:
        ch_text = "/d"
    channel_id = await parse_target_id(client, ch_text, m.chat.id)

    await editable.delete()

    # topic index structure
    topic_index = defaultdict(list)
    failed = 0
    sent_count = 0

    # Process links
    for idx in range(start_idx-1, len(links)):
        raw_name, url = links[idx]
        topic = extract_topic(raw_name)
        safe_name = sanitize_filename(raw_name)
        file_name_base = safe_name[:60]

        # Caption sections (topic first)
        topic_section = f"<b>Topic:</b> {topic}\n"
        file_section = f"<b>File:</b> {safe_name}\n"
        batch_section = f"<pre>📘 ʙᴀᴛᴄʜ : {b_name}</pre>\n"
        caption_common = (
            "━━━━━━━━━━━━━━━━━━━━━━━\n" +
            topic_section +
            file_section +
            batch_section +
            "━━━━━━━━━━━━━━━━━━━━━━━\n" +
            f"<b>👤 Uploaded By: 🔥 <a href='https://t.me/MrsUC'>𝙈𝙧𝙨.𝙐𝘾 ❣️</a></b>\n"
        )

        try:
            # delegate download to helper (keeps your logic)
            # try to infer a default command; helper should handle best quality selection internally
            download_cmd = f'yt-dlp -f "best" "{url}" -o "{file_name_base}.mp4"'
            result_file = await helper.download_video(url, download_cmd, file_name_base)
            # send video
                        # ensure per-topic thread
            thread_id = None
            if is_forum:
                if topic not in topic_threads:
                    topic_threads[topic] = await get_or_create_forum_topic(bot, channel_id, topic)
                thread_id = topic_threads.get(topic)
            sent_msg = await helper.send_vid(bot, m, caption_common, result_file, "/d", file_name_base, None, channel_id, watermark=watermark, message_thread_id=thread_id)

            if getattr(sent_msg, "id", None):
                link = await build_message_link(bot, channel_id, sent_msg.id)
            else:
                info = await bot.send_message(channel_id, f\"Uploaded: {safe_name}\", message_thread_id=thread_id)
                link = await build_message_link(bot, channel_id, info.id)

            # store first (DB + JSON), then continue
            topic_index[topic].append({"title": f"{topic} | {safe_name}", "link": link})
            try_db_save_index(b_name, topic_index)
            persist_topic_index_json(b_name, topic_index)
            sent_count += 1

            # optional small delay
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            await bot.send_message(channel_id, f"⚠️ Failed: {safe_name}\n{e}")
            failed += 1
            continue

    # Summary
        except Exception as e:
        try:
            await m.reply_text(f"DRM error: {e}")
        except Exception:
            pass

    summary = (
        "<b>✨ Process Completed</b>\n\n"
        f"<blockquote><b>📌 Batch:</b> {b_name}</blockquote>\n"
        "╭────────────────\n"
        f"├ 🔗 Total URLs : <code>{len(links)}</code>\n"
        f"├ 🟢 Successful : <code>{sent_count}</code>\n"
        f"├ ❌ Failed     : <code>{failed}</code>\n"
        "╰────────────────\n\n"
        "<i>Extracted by Mr.UC ⚙️</i>"
    )
    await bot.send_message(channel_id, summary, disable_web_page_preview=True)

    # Post Topic-wise index (split if too long)
    if topic_index:
        def chunk_send(lines, title=None):
            page = []
            if title:
                page.append(f"<b>{title}</b>")
            for ln in lines:
                page.append(ln)
            text = "\n".join(page)
            if len(text) <= 3900:
                return [text]
            # crude split
            parts, buf = [], []
            cur_len = 0
            for ln in page:
                if cur_len + len(ln) + 1 > 3900:
                    parts.append("\n".join(buf))
                    buf, cur_len = [ln], len(ln)
                else:
                    buf.append(ln)
                    cur_len += len(ln) + 1
            if buf: parts.append("\n".join(buf))
            return parts

        for tpc, items in topic_index.items():
            lines = [f"• <b>{tpc}</b>"]
            for it in items:
                title = it.get("title", "")
                link = it.get("link", "")
                short = (title[:80] + "…") if len(title) > 80 else title
                lines.append(f"  ─ <a href='{link}'>{short}</a>")
            for part in chunk_send(lines):
                await bot.send_message(channel_id, part, disable_web_page_preview=True)

    if m.chat.type == "private":
        await bot.send_message(m.chat.id, f"✅ Done! Check target chat/channel: {channel_id}")

# ------------------ Run ------------------
if __name__ == "__main__":
    print("Starting Bot...")
    bot.run()


@bot.on_message(filters.command("health") & (filters.private | filters.group | filters.channel))
async def health(client, m):
    try:
        me = await client.get_me()
        await m.reply_text(f"OK ✅\nBot: @{me.username}\nChat: {m.chat.id}")
    except Exception as e:
        await m.reply_text(f"Health error: {e}")
