import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
MAX_ACTIVE_USERS = int(os.getenv("MAX_ACTIVE_USERS", "10"))
DB_PATH = os.getenv("DB_PATH", "bot.sqlite3")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("maktab-yordamchisi")

NAME, SCHOOL, SUBJECT = range(3)


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_TELEGRAM_ID) and str(user_id) == ADMIN_TELEGRAM_ID


def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(db()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                school TEXT NOT NULL,
                subject TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by INTEGER
            )
        """)
        conn.commit()


def user_row(telegram_id: int):
    with closing(db()) as conn:
        return conn.execute(
            "SELECT telegram_id, username, full_name, school, subject, status "
            "FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def active_count() -> int:
    with closing(db()) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE status = 'approved'"
        ).fetchone()[0]


def save_request(telegram_id: int, username: str, full_name: str, school: str, subject: str):
    with closing(db()) as conn:
        conn.execute("""
            INSERT INTO users
            (telegram_id, username, full_name, school, subject, status, requested_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                school=excluded.school,
                subject=excluded.subject,
                status='pending',
                requested_at=excluded.requested_at,
                decided_at=NULL,
                decided_by=NULL
        """, (
            telegram_id, username, full_name, school, subject,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()


def decide_user(telegram_id: int, status: str, admin_id: int):
    with closing(db()) as conn:
        conn.execute(
            "UPDATE users SET status=?, decided_at=?, decided_by=? WHERE telegram_id=?",
            (status, datetime.now(timezone.utc).isoformat(), admin_id, telegram_id)
        )
        conn.commit()


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📊 eMaktab statistikasi"), KeyboardButton("📚 Ta’lim yordamchisi")],
            [KeyboardButton("📝 Hisobotlar"), KeyboardButton("⚙️ Mening profilim")],
        ],
        resize_keyboard=True
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_admin(user.id):
        await update.message.reply_text(
            "Assalomu alaykum, administrator!\\n\\n"
            f"Faol a’zolar: {active_count()}/{MAX_ACTIVE_USERS}\\n"
            "Yangi arizalar shu chatga keladi. /pending — kutilayotgan arizalar.",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END

    row = user_row(user.id)
    if row:
        status = row[5]
        if status == "approved":
            await update.message.reply_text(
                "Xush kelibsiz! Sizning akkauntingiz tasdiqlangan.",
                reply_markup=main_keyboard()
            )
        elif status == "pending":
            await update.message.reply_text("Arizangiz administrator tasdig‘ini kutmoqda. Tasdiqlangach xabar beraman.")
        elif status == "rejected":
            await update.message.reply_text("Arizangiz rad etilgan. Qayta ariza berish uchun /apply buyrug‘ini yuboring.")
        elif status == "blocked":
            await update.message.reply_text("Akkauntingiz bloklangan. Administrator bilan bog‘laning.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Maktab Yordamchisi botiga xush kelibsiz!\\n"
        "Botdan foydalanish uchun ariza yuboring. Administrator tasdiqlagandan keyin akkauntingiz faollashadi.\\n\\n"
        "Arizani boshlash uchun /apply buyrug‘ini yuboring."
    )
    return ConversationHandler.END


async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_admin(user.id):
        await update.message.reply_text("Siz administrator hisoblanasiz.")
        return ConversationHandler.END

    row = user_row(user.id)
    if row and row[5] == "approved":
        await update.message.reply_text("Siz allaqachon tasdiqlangansiz.", reply_markup=main_keyboard())
        return ConversationHandler.END
    if row and row[5] == "blocked":
        await update.message.reply_text("Akkauntingiz bloklangan.")
        return ConversationHandler.END

    await update.message.reply_text("Ism-familiyangizni kiriting:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if len(value) < 3 or len(value) > 100:
        await update.message.reply_text("Iltimos, ism-familiyangizni 3–100 belgi oralig‘ida kiriting.")
        return NAME
    context.user_data["full_name"] = value
    await update.message.reply_text("Maktabingiz nomi yoki raqamini kiriting:")
    return SCHOOL


async def get_school(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text.strip()
    if len(value) < 2 or len(value) > 150:
        await update.message.reply_text("Maktab nomini 2–150 belgi oralig‘ida kiriting.")
        return SCHOOL
    context.user_data["school"] = value
    await update.message.reply_text("Qaysi fan(lar)dan dars berasiz?")
    return SUBJECT


async def get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    subject = update.message.text.strip()
    if len(subject) < 2 or len(subject) > 150:
        await update.message.reply_text("Fan nomini 2–150 belgi oralig‘ida kiriting.")
        return SUBJECT

    save_request(
        user.id, user.username or "", context.user_data["full_name"],
        context.user_data["school"], subject
    )
    await update.message.reply_text(
        "Arizangiz administratorga yuborildi. Tasdiqlanguncha botning asosiy funksiyalari yopiq."
    )

    if ADMIN_TELEGRAM_ID:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve:{user.id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject:{user.id}")
        ]])
        admin_text = (
            "🆕 Yangi a’zo arizasi\\n\\n"
            f"Ism-familiya: {context.user_data['full_name']}\\n"
            f"Maktab: {context.user_data['school']}\\n"
            f"Fan(lar): {subject}\\n"
            f"Telegram ID: {user.id}\\n"
            f"Username: @{user.username}" if user.username else
            "🆕 Yangi a’zo arizasi\\n\\n"
            f"Ism-familiya: {context.user_data['full_name']}\\n"
            f"Maktab: {context.user_data['school']}\\n"
            f"Fan(lar): {subject}\\n"
            f"Telegram ID: {user.id}\\nUsername: yo‘q"
        )
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_TELEGRAM_ID),
                text=admin_text,
                reply_markup=keyboard
            )
        except Exception:
            log.exception("Administratorga ariza yuborilmadi. ADMIN_TELEGRAM_ID ni tekshiring.")
    else:
        log.error("ADMIN_TELEGRAM_ID sozlanmagan; arizalar admin chatiga yuborilmaydi.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Ariza bekor qilindi. Qayta boshlash uchun /apply yuboring.")
    return ConversationHandler.END


async def review_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin = update.effective_user
    if not is_admin(admin.id):
        await query.edit_message_text("Bu amal faqat administrator uchun.")
        return

    try:
        action, raw_id = query.data.split(":", 1)
        target_id = int(raw_id)
    except (ValueError, AttributeError):
        await query.edit_message_text("Ariza tugmasi noto‘g‘ri.")
        return

    row = user_row(target_id)
    if not row:
        await query.edit_message_text("Foydalanuvchi topilmadi.")
        return

    if action == "approve":
        if row[5] == "approved":
            await query.edit_message_text("Bu foydalanuvchi allaqachon tasdiqlangan.")
            return
        if active_count() >= MAX_ACTIVE_USERS:
            await query.edit_message_text(
                f"Faol a’zolar limiti to‘lgan ({MAX_ACTIVE_USERS}). Avval bir a’zoni bloklang."
            )
            return
        decide_user(target_id, "approved", admin.id)
        await query.edit_message_text(f"✅ Tasdiqlandi: {row[2]} (ID: {target_id})")
        try:
            await context.bot.send_message(
                target_id,
                "🎉 Arizangiz tasdiqlandi! Endi Maktab Yordamchisi botidan foydalanishingiz mumkin.",
                reply_markup=main_keyboard()
            )
        except Exception:
            log.exception("Tasdiq xabari foydalanuvchiga yuborilmadi.")
    elif action == "reject":
        decide_user(target_id, "rejected", admin.id)
        await query.edit_message_text(f"❌ Ariza rad etildi: {row[2]}")
        try:
            await context.bot.send_message(target_id, "Arizangiz rad etildi. Savolingiz bo‘lsa administratorga murojaat qiling.")
        except Exception:
            log.exception("Rad javobi foydalanuvchiga yuborilmadi.")


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat administrator uchun.")
        return
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT telegram_id, full_name, school, subject, requested_at "
            "FROM users WHERE status='pending' ORDER BY requested_at"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Kutilayotgan arizalar yo‘q.")
        return
    for r in rows:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve:{r[0]}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject:{r[0]}")
        ]])
        await update.message.reply_text(
            f"Ariza: {r[1]}\\nMaktab: {r[2]}\\nFan: {r[3]}\\nID: {r[0]}",
            reply_markup=keyboard
        )


async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat administrator uchun.")
        return
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT telegram_id, full_name, status FROM users ORDER BY full_name"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Hali a’zolar yo‘q.")
        return
    text = [f"Faol a’zolar: {active_count()}/{MAX_ACTIVE_USERS}", ""]
    for uid, name, status in rows:
        text.append(f"{name} | {uid} | {status}")
    text.append("\\nBloklash: /block TELEGRAM_ID")
    await update.message.reply_text("\\n".join(text))


async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bu buyruq faqat administrator uchun.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /block TELEGRAM_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Telegram ID raqam bo‘lishi kerak.")
        return
    if target_id == update.effective_user.id:
        await update.message.reply_text("Administrator o‘zini bloklay olmaydi.")
        return
    with closing(db()) as conn:
        cur = conn.execute(
            "UPDATE users SET status='blocked', decided_at=?, decided_by=? WHERE telegram_id=?",
            (datetime.now(timezone.utc).isoformat(), update.effective_user.id, target_id)
        )
        conn.commit()
    if cur.rowcount:
        await update.message.reply_text(f"{target_id} bloklandi.")
        try:
            await context.bot.send_message(target_id, "Administrator botdan foydalanish ruxsatingizni bekor qildi.")
        except Exception:
            pass
    else:
        await update.message.reply_text("Bunday foydalanuvchi topilmadi.")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_admin(user.id):
        await update.message.reply_text("Administrator menyusi.", reply_markup=main_keyboard())
        return
    row = user_row(user.id)
    if not row or row[5] != "approved":
        await update.message.reply_text("Botdan foydalanish uchun administrator tasdig‘i kerak. /start")
        return

    text = update.message.text
    if text == "⚙️ Mening profilim":
        await update.message.reply_text(
            f"Ism: {row[2]}\\nMaktab: {row[3]}\\nFan: {row[4]}\\nHolat: tasdiqlangan"
        )
    elif text == "📚 Ta’lim yordamchisi":
        await update.message.reply_text(
            "Ta’lim yordamchisi keyingi bosqichda ulanadi. Hozircha savolni shu chatga matn yoki rasm sifatida yuborish mumkin; AI API hali sozlanmagan."
        )
    elif text == "📊 eMaktab statistikasi":
        await update.message.reply_text(
            "Statistika moduli keyingi bosqichda ulanadi. Hozircha eMaktabdan eksport qilingan hisobotni tahlil qilish funksiyasini qo‘shamiz."
        )
    elif text == "📝 Hisobotlar":
        await update.message.reply_text("Hisobotlar moduli keyingi bosqichda ulanadi.")
    else:
        await update.message.reply_text("Menyudan birini tanlang yoki /help yuboring.", reply_markup=main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — botni boshlash\\n"
        "/apply — a’zolik uchun ariza\\n"
        "/cancel — arizani bekor qilish\\n\\n"
        "Administrator: /pending, /members, /block TELEGRAM_ID"
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini sozlang.")
    if not ADMIN_TELEGRAM_ID.isdigit():
        raise SystemExit("ADMIN_TELEGRAM_ID .env faylida raqamli Telegram ID bo‘lishi kerak.")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    application_form = ConversationHandler(
        entry_points=[CommandHandler("apply", apply_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SCHOOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_school)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subject)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(application_form)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CallbackQueryHandler(review_application, pattern=r"^(approve|reject):\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))

    log.info("Maktab Yordamchisi bot ishga tushmoqda.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
