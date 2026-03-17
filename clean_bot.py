#!/usr/bin/env python3
"""
Telegram Clean Bot v3
- Super Admin: barcha guruhlarni boshqaradi (private chat panel)
- Guruh adminlari: faqat o'z guruhini boshqaradi (/panel)
- Statistika JSON da saqlanadi
"""

import logging
import json
import os
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.error import TelegramError

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8370425802:AAEfi3UD3tj7RXKJI5yK5QkEv6e8_9BxvCw"
SUPER_ADMIN_ID = 1914849129
STATS_FILE = "clean_bot_stats.json"
# ====================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ===================== JSON DB =====================
def load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_stats(data: dict):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_chat(chat_id: int) -> dict:
    stats = load_stats()
    key = str(chat_id)
    if key not in stats:
        stats[key] = {
            "chat_title": "",
            "join_deleted": 0,
            "left_deleted": 0,
            "delete_join": True,
            "delete_left": True,
            "enabled": True,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_stats(stats)
    return stats[key]

def set_field(chat_id: int, field: str, value):
    stats = load_stats()
    key = str(chat_id)
    if key not in stats:
        get_chat(chat_id)
        stats = load_stats()
    stats[key][field] = value
    save_stats(stats)

def increment(chat_id: int, field: str):
    stats = load_stats()
    key = str(chat_id)
    if key not in stats:
        get_chat(chat_id)
        stats = load_stats()
    stats[key][field] = stats[key].get(field, 0) + 1
    save_stats(stats)


# ===================== HELPERS =====================
async def is_group_admin(context, chat_id: int, user_id: int) -> bool:
    if user_id == SUPER_ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)
    except Exception:
        return False


def chat_panel_text(chat_id: int, title: str) -> str:
    s = get_chat(chat_id)
    st = "🟢 Ishlayapti" if s["enabled"] else "🔴 To'xtatilgan"
    jt = "✅" if s["delete_join"] else "❌"
    lt = "✅" if s["delete_left"] else "❌"
    return (
        f"⚙️ *{title}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Statistika:*\n"
        f"  👋 Kirdi o'chirildi: `{s['join_deleted']}`\n"
        f"  🚪 Chiqdi o'chirildi: `{s['left_deleted']}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔧 *Sozlamalar:*\n"
        f"  Holat: {st}\n"
        f"  Kirdi: {jt}   Chiqdi: {lt}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M')}`"
    )


def chat_panel_kb(chat_id: int, source: str = "group") -> InlineKeyboardMarkup:
    # source = "group" | "superadmin"
    s = get_chat(chat_id)
    btn_bot   = "🔴 Botni o'chir" if s["enabled"]     else "🟢 Botni yoq"
    btn_join  = f"👋 Kirdi: {'✅' if s['delete_join'] else '❌'}"
    btn_left  = f"🚪 Chiqdi: {'✅' if s['delete_left'] else '❌'}"

    prefix = f"{source}|{chat_id}"
    kb = [
        [InlineKeyboardButton(btn_bot,  callback_data=f"toggle_bot|{prefix}")],
        [
            InlineKeyboardButton(btn_join, callback_data=f"toggle_join|{prefix}"),
            InlineKeyboardButton(btn_left, callback_data=f"toggle_left|{prefix}"),
        ],
        [InlineKeyboardButton("🗑 Statistikani tozala", callback_data=f"reset_stats|{prefix}")],
        [InlineKeyboardButton("🔄 Yangilash",           callback_data=f"refresh|{prefix}")],
    ]
    if source == "superadmin":
        kb.append([InlineKeyboardButton("◀️ Orqaga — guruhlar ro'yxati", callback_data="sa_list|0")])
    return InlineKeyboardMarkup(kb)


# =================== SUPER ADMIN PANEL ===================
def sa_list_text(page: int, chats: list) -> str:
    total_j = sum(c[1].get("join_deleted", 0) for c in chats)
    total_l = sum(c[1].get("left_deleted", 0) for c in chats)
    return (
        f"🛠 *Super Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Jami guruhlar: `{len(chats)}`\n"
        f"👋 Jami kirdi o'chirildi: `{total_j}`\n"
        f"🚪 Jami chiqdi o'chirildi: `{total_l}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Guruhni tanlang:"
    )


def sa_list_kb(page: int, chats: list) -> InlineKeyboardMarkup:
    PAGE_SIZE = 8
    start = page * PAGE_SIZE
    end   = start + PAGE_SIZE
    chunk = chats[start:end]

    rows = []
    for chat_id, s in chunk:
        icon  = "🟢" if s.get("enabled", True) else "🔴"
        title = (s.get("chat_title") or str(chat_id))[:28]
        rows.append([InlineKeyboardButton(
            f"{icon} {title}",
            callback_data=f"sa_open|{chat_id}|{page}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"sa_list|{page-1}"))
    if end < len(chats):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"sa_list|{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔄 Yangilash", callback_data=f"sa_list|{page}")])
    return InlineKeyboardMarkup(rows)


# =================== KIRDI/CHIQDI O'CHIRISH ===================
async def handle_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat_id = msg.chat_id
    s = get_chat(chat_id)

    # Guruh nomini yangilab tur
    if msg.chat.title:
        set_field(chat_id, "chat_title", msg.chat.title)

    if not s.get("enabled", True):
        return

    should_delete = False
    kind = None

    if msg.new_chat_members and s.get("delete_join", True):
        should_delete = True
        kind = "join"
    elif msg.left_chat_member and s.get("delete_left", True):
        should_delete = True
        kind = "left"

    if should_delete:
        try:
            await msg.delete()
            increment(chat_id, "join_deleted" if kind == "join" else "left_deleted")
            logger.info(f"✅ [{kind}] o'chirildi | {chat_id}")
        except TelegramError as e:
            logger.warning(f"❌ O'chirishda xato: {e}")


# =================== BOT GURUHGA QO'SHILDI ===================
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new_status = result.new_chat_member.status

    if new_status in (ChatMember.ADMINISTRATOR, ChatMember.MEMBER):
        # Botni guruhga qo'shishdi yoki admin qilishdi
        s = get_chat(chat.id)
        set_field(chat.id, "chat_title", chat.title or str(chat.id))
        logger.info(f"Bot guruhga qo'shildi: {chat.title} ({chat.id})")
        try:
            await context.bot.send_message(
                chat_id=SUPER_ADMIN_ID,
                text=(
                    f"➕ *Bot yangi guruhga qo'shildi!*\n\n"
                    f"📌 Guruh: *{chat.title}*\n"
                    f"🆔 ID: `{chat.id}`"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass
    elif new_status in (ChatMember.LEFT, ChatMember.BANNED):
        logger.info(f"Bot guruhdan chiqarildi: {chat.title} ({chat.id})")
        try:
            await context.bot.send_message(
                chat_id=SUPER_ADMIN_ID,
                text=(
                    f"➖ *Bot guruhdan chiqarildi!*\n\n"
                    f"📌 Guruh: *{chat.title}*\n"
                    f"🆔 ID: `{chat.id}`"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass


# =================== KOMANDALAR ===================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != "private":
        return

    if user.id == SUPER_ADMIN_ID:
        # Super admin panelni ko'rsatamiz
        await show_sa_list(update, context, page=0, edit=False)
        return

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Guruhga qo'shish",
            url=f"https://t.me/{bot_username}?startgroup=true"
        )],

    ])

    await update.message.reply_text(
        "🚫 *Kirdi — Chiqdi Tozalovchi Bot*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Guruhingizga yangi a'zo qo'shildi yoki kimdir chiqib ketdi — "
        "bu xabarlar guruhni ifloslantiradi. "
        "Men ularni *avtomatik ravishda* o'chirib turaman! 🧹\n\n"
        "⚡️ *Imkoniyatlar:*\n"
        "  ✅ «Qo'shildi» xabarlarini o'chirish\n"
        "  ✅ «Chiqdi» xabarlarini o'chirish\n"
        "  ✅ Har bir guruh uchun alohida sozlama\n"
        "  ✅ Statistika — nechta o'chirilganini ko'rish\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 *Ishlatish — 3 qadam:*\n\n"
        "1️⃣ Quyidagi tugma orqali botni guruhga qo'shing\n"
        "2️⃣ Botga *«Xabarlarni o'chirish»* admin huquqini bering\n"
        "3️⃣ Guruhda `/panel` yozing — sozlang va tayyor!\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🤖 Bot ishlayapti va buyruqlaringizni kutmoqda.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh adminlari uchun — guruhda chaqiriladi"""
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        if user.id == SUPER_ADMIN_ID:
            await show_sa_list(update, context, page=0, edit=False)
        return

    if not await is_group_admin(context, chat.id, user.id):
        try:
            await update.message.reply_text("❌ Faqat adminlar uchun.")
        except Exception:
            pass
        return

    set_field(chat.id, "chat_title", chat.title or str(chat.id))

    text  = chat_panel_text(chat.id, chat.title or "Guruh")
    markup = chat_panel_kb(chat.id, source="group")

    try:
        await update.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=markup,
        parse_mode="Markdown"
    )


# =================== SUPER ADMIN YORDAMCHI ===================
async def show_sa_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, edit: bool):
    all_stats = load_stats()
    chats = sorted(all_stats.items(), key=lambda x: x[1].get("chat_title", ""))

    text   = sa_list_text(page, chats)
    markup = sa_list_kb(page, chats)

    if edit:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=markup, parse_mode="Markdown"
            )
        except TelegramError:
            pass
    else:
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg:
            await msg.reply_text(text, reply_markup=markup, parse_mode="Markdown")


# =================== CALLBACK HANDLER ===================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("|")
    action = parts[0]

    # ---- Super admin ro'yxat ----
    if action == "sa_list":
        if update.effective_user.id != SUPER_ADMIN_ID:
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        page = int(parts[1]) if len(parts) > 1 else 0
        await show_sa_list(update, context, page=page, edit=True)
        return

    # ---- Super admin guruh ochish ----
    if action == "sa_open":
        if update.effective_user.id != SUPER_ADMIN_ID:
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        chat_id = int(parts[1])
        s = get_chat(chat_id)
        title = s.get("chat_title") or str(chat_id)
        text   = chat_panel_text(chat_id, title)
        markup = chat_panel_kb(chat_id, source="superadmin")
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        except TelegramError as e:
            logger.warning(f"sa_open edit xato: {e}")
        return

    # ---- Guruh panel tugmalari ----
    # format: action|source|chat_id
    if len(parts) < 3:
        return

    source  = parts[1]   # "group" | "superadmin"
    chat_id = int(parts[2])

    # Ruxsat tekshirish
    user_id = update.effective_user.id
    if source == "superadmin":
        if user_id != SUPER_ADMIN_ID:
            await query.answer("❌ Faqat super admin!", show_alert=True)
            return
    else:
        if not await is_group_admin(context, chat_id, user_id):
            await query.answer("❌ Faqat adminlar!", show_alert=True)
            return

    s = get_chat(chat_id)

    if action == "toggle_bot":
        new_val = not s.get("enabled", True)
        set_field(chat_id, "enabled", new_val)
        await query.answer("🟢 Yoqildi" if new_val else "🔴 O'chirildi")

    elif action == "toggle_join":
        new_val = not s.get("delete_join", True)
        set_field(chat_id, "delete_join", new_val)
        await query.answer(f"👋 Kirdi: {'✅' if new_val else '❌'}")

    elif action == "toggle_left":
        new_val = not s.get("delete_left", True)
        set_field(chat_id, "delete_left", new_val)
        await query.answer(f"🚪 Chiqdi: {'✅' if new_val else '❌'}")

    elif action == "reset_stats":
        set_field(chat_id, "join_deleted", 0)
        set_field(chat_id, "left_deleted", 0)
        await query.answer("🗑 Statistika tozalandi!", show_alert=True)

    elif action == "refresh":
        await query.answer("🔄 Yangilandi")

    # Panelni yangilash
    try:
        chat_obj = await context.bot.get_chat(chat_id)
        title  = chat_obj.title or str(chat_id)
        text   = chat_panel_text(chat_id, title)
        markup = chat_panel_kb(chat_id, source=source)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    except TelegramError as e:
        logger.warning(f"Panel yangilash xato: {e}")


# =================== POST INIT ===================
async def post_init(application: Application):
    logger.info("🤖 Clean Bot v3 ishga tushdi!")
    try:
        await application.bot.send_message(
            chat_id=SUPER_ADMIN_ID,
            text=(
                "🟢 *Clean Bot v3 ishga tushdi!*\n\n"
                "Barcha guruhlarni boshqarish uchun /start yozing."
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass


# =================== MAIN ===================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Kirdi/chiqdi xabarlarini o'chirish
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_service_message
    ))

    # Bot guruhga qo'shildi/chiqarildi
    from telegram.ext import ChatMemberHandler
    app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Komandalar
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("panel",  cmd_panel))

    # Inline callback
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Polling boshlandi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
