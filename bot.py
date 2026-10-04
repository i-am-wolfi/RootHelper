# RootHelper — group helper for ROM groups (Bot API)
# Token e IDs via ambiente (NUNCA commitar): BOT_TOKEN, OWNER_ID

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOG = logging.getLogger("roothelper")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0") or 0)
DATA = Path(os.environ.get("DATA_DIR", "data"))
DATA.mkdir(exist_ok=True)

app = Client("roothelper", bot_token=BOT_TOKEN, in_memory=True)


def _load(name, default):
    p = DATA / f"{name}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return default


def _save(name, obj):
    (DATA / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2))


rules_db = _load("rules", {})
notes_db = _load("notes", {})
warns_db = _load("warns", {})
flood_db = {}  # chat_id -> {user_id: [timestamps]}


def is_admin(chat_id, user_id):
    return user_id == OWNER_ID


@app.on_message(filters.command("start"))
async def start_(c, m):
    await m.reply(
        "🤖 **RootHelper** — helper para grupos de ROMs\n\n"
        "Comandos: /rules /report /note /warn /pin\n"
        "ROMs: /ofox /los /cr /axion /ksu /lsp /apatch",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📕 Regras", callback_data="show_rules")]]),
    )


@app.on_message(filters.command("rules"))
async def rules_(c, m):
    text = rules_db.get(str(m.chat.id), "📌 Sem regras definidas. Admins: /setrules <texto>")
    await m.reply(f"📕 **Regras**\n\n{text}")


@app.on_message(filters.command("setrules") & filters.group)
async def setrules_(c, m):
    member = await c.get_chat_member(m.chat.id, m.from_user.id)
    if member.status not in ("administrator", "creator") and m.from_user.id != OWNER_ID:
        return
    text = m.text.split(None, 1)
    if len(text) < 2:
        await m.reply("Uso: `/setrules <texto>`")
        return
    rules_db[str(m.chat.id)] = text[1]
    _save("rules", rules_db)
    await m.reply("✅ Regras salvas.")


@app.on_callback_query(filters.regex("show_rules"))
async def show_rules_cb(c, q):
    text = rules_db.get(str(q.message.chat.id), "📌 Sem regras definidas.")
    await q.answer(text[:190], show_alert=True)


@app.on_message(filters.new_chat_members)
async def welcome_(c, m):
    for u in m.new_chat_members:
        if u.is_bot:
            continue
        rules = rules_db.get(str(m.chat.id))
        txt = f"👋 Bem-vindo(a), {u.mention}!\n"
        txt += "📕 Leia as regras com /rules" if rules else "Use /rules para ver as regras."
        await m.reply(txt)


@app.on_message(filters.command("report") & filters.group)
async def report_(c, m):
    if not m.reply_to_message:
        await m.reply("Responda a mensagem a denunciar com /report.")
        return
    try:
        admins = [a.user.id async for a in c.get_chat_members(m.chat.id, filter="administrators") if not a.user.is_bot]
    except Exception:
        admins = []
    if not admins:
        await m.reply("Não achei admins para marcar.")
        return
    mentions = " ".join(f"[.](tg://user?id={a})" for a in admins)
    await m.reply(
        f"🚨 **Denúncia** de {m.from_user.mention} contra {m.reply_to_message.from_user.mention}\n{mentions}",
    )


@app.on_message(filters.command(["note", "addnote"]) & filters.group)
async def addnote_(c, m):
    member = await c.get_chat_member(m.chat.id, m.from_user.id)
    if member.status not in ("administrator", "creator") and m.from_user.id != OWNER_ID:
        return
    parts = m.text.split(None, 2)
    if len(parts) < 3:
        await m.reply("Uso: `/note <gatilho> <texto>`  ex: `/note gapps use ,ngapps`")
        return
    notes_db.setdefault(str(m.chat.id), {})[parts[1].lower()] = parts[2]
    _save("notes", notes_db)
    await m.reply(f"✅ Nota `!{parts[1].lower()}` salva.")


@app.on_message(filters.command("delnote") & filters.group)
async def delnote_(c, m):
    parts = m.text.split(None, 1)
    notes = notes_db.get(str(m.chat.id), {})
    if len(parts) < 2 or parts[1].lower() not in notes:
        await m.reply("Uso: `/delnote <gatilho>`")
        return
    del notes[parts[1].lower()]
    _save("notes", notes_db)
    await m.reply("✅ Nota removida.")


@app.on_message(filters.group & filters.text & ~filters.service)
async def notes_watch(c, m):
    text = (m.text or "").strip()
    if text.startswith("!") and len(text) > 1:
        note = notes_db.get(str(m.chat.id), {}).get(text[1:].split()[0].lower())
        if note:
            await m.reply(note)
            return
    # antiflood: 6+ msgs em 10s -> apaga excedentes e avisa
    now = time.time()
    box = flood_db.setdefault(m.chat.id, {}).setdefault(m.from_user.id, [])
    box[:] = [t for t in box if now - t < 10]
    box.append(now)
    if len(box) == 6:
        try:
            await m.delete()
        except Exception:
            pass
        await c.send_message(m.chat.id, f"🐢 {m.from_user.mention}, devagar! Flood detectado.")


@app.on_message(filters.command("warn") & filters.group)
async def warn_(c, m):
    member = await c.get_chat_member(m.chat.id, m.from_user.id)
    if member.status not in ("administrator", "creator") and m.from_user.id != OWNER_ID:
        return
    target = m.reply_to_message.from_user if m.reply_to_message else None
    if not target:
        await m.reply("Responda ao usuário com /warn.")
        return
    key = f"{m.chat.id}:{target.id}"
    warns_db[key] = warns_db.get(key, 0) + 1
    _save("warns", warns_db)
    n = warns_db[key]
    if n >= 3:
        try:
            await c.restrict_chat_member(m.chat.id, target.id, permissions=None)
            await m.reply(f"🔇 {target.mention} mutado após 3 warns.")
        except Exception as e:
            await m.reply(f"Warn {n}/3, mas falhei ao mutar: `{e}`")
    else:
        await m.reply(f"⚠️ Warn {n}/3 para {target.mention}.")


@app.on_message(filters.command("unwarn") & filters.group)
async def unwarn_(c, m):
    member = await c.get_chat_member(m.chat.id, m.from_user.id)
    if member.status not in ("administrator", "creator") and m.from_user.id != OWNER_ID:
        return
    target = m.reply_to_message.from_user if m.reply_to_message else None
    if not target:
        await m.reply("Responda ao usuário com /unwarn.")
        return
    warns_db.pop(f"{m.chat.id}:{target.id}", None)
    _save("warns", warns_db)
    await m.reply(f"✅ Warns de {target.mention} zerados.")


@app.on_message(filters.command("pin") & filters.group)
async def pin_(c, m):
    if not m.reply_to_message:
        await m.reply("Responda a mensagem com /pin.")
        return
    try:
        await c.pin_chat_message(m.chat.id, m.reply_to_message.id)
        await m.reply("📌 Fixada.")
    except Exception as e:
        await m.reply(f"Falha ao fixar (preciso ser admin com direito de fixar): `{e}`")


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN não definido. Exporte BOT_TOKEN ou crie bot.env")
    await app.start()
    LOG.info("RootHelper on: @%s", (await app.get_me()).username)
    await asyncio.Event().wait()


if __name__ == "__main__":
    app.run(main())
