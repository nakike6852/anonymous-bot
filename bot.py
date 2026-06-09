import telebot
from telebot import types
import sqlite3
import time
import datetime

# ===== تنظیمات =====
TOKEN = "8329995313:AAEiy9hH7Jt7COrmqUfTTvZ7XMn_NZvSyvE"
ADMIN_ID = 8417718642
BOT_USERNAME = "ChatePrivate_Bot"

BAD_WORDS = ["فحش۱", "فحش۲", "فحش۳"]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ===== وضعیت ربات =====
bot_status = {"active": True, "maintenance": False}
welcome_text = "👋 <b>خوش آمدی!</b>\n\n📩 هر پیامی بفرستی <b>ناشناس</b> برای ادمین ارسال میشه ✅\n\n🔒 هویت شما کاملاً محفوظ است."

# ===== دیتابیس =====
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    banned INTEGER DEFAULT 0,
    ban_until INTEGER DEFAULT 0,
    msg_count INTEGER DEFAULT 0,
    last_activity TEXT DEFAULT '',
    join_date TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content_type TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reply_map (
    admin_message_id INTEGER PRIMARY KEY,
    user_id INTEGER
)
""")

conn.commit()

# ===== توابع کمکی =====
def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def register_user(user):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.full_name, get_time()))
    cursor.execute(
        "UPDATE users SET username=?, full_name=? WHERE user_id=?",
        (user.username, user.full_name, user.id))
    conn.commit()

def is_banned(user_id):
    cursor.execute("SELECT banned, ban_until FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    if not data:
        return False
    if data[0] == 1:
        if data[1] > 0 and int(time.time()) > data[1]:
            cursor.execute("UPDATE users SET banned=0, ban_until=0 WHERE user_id=?", (user_id,))
            conn.commit()
            return False
        return True
    return False

def has_bad_words(text):
    if not text:
        return False
    for word in BAD_WORDS:
        if word in text:
            return True
    return False

def get_msg_number(user_id):
    cursor.execute("UPDATE users SET msg_count = msg_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM messages")
    return cursor.fetchone()[0] + 1

def get_reply_user_id(admin_message_id):
    cursor.execute("SELECT user_id FROM reply_map WHERE admin_message_id=?", (admin_message_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def show_username(username):
    return f"@{username}" if username else "ندارد"

# ===== استارت =====
@bot.message_handler(commands=['start'])
def start(message):
    if bot_status["maintenance"] and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "🔧 ربات در حال تعمیر است.")
        return

    register_user(message.from_user)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📩 ارسال پیام ناشناس",
               url=f"https://t.me/{BOT_USERNAME}"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# ===== پنل ادمین =====
@bot.message_handler(commands=['panel'])
def panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    show_panel(message.chat.id)

def show_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کلی", callback_data="stats"),
        types.InlineKeyboardButton("📈 آمار روزانه", callback_data="daily_stats")
    )
    markup.add(
        types.InlineKeyboardButton("👥 آخرین کاربران", callback_data="recent_users"),
        types.InlineKeyboardButton("🚫 لیست بن", callback_data="banlist")
    )
    markup.add(
        types.InlineKeyboardButton("📢 برودکست", callback_data="broadcast"),
        types.InlineKeyboardButton("✏️ تغییر خوش‌آمد", callback_data="change_welcome")
    )

    status = "🟢 فعال" if bot_status["active"] else "🔴 غیرفعال"
    maint = "🔧 تعمیر" if bot_status["maintenance"] else "✅ عادی"

    markup.add(
        types.InlineKeyboardButton(f"وضعیت: {status}", callback_data="toggle_bot"),
        types.InlineKeyboardButton(f"حالت: {maint}", callback_data="toggle_maintenance")
    )
    markup.add(types.InlineKeyboardButton("🔙 بستن پنل", callback_data="close_panel"))

    bot.send_message(chat_id,
                     "🎛 <b>پنل مدیریت حرفه‌ای</b>\n\n"
                     f"وضعیت ربات: {status}\n"
                     f"حالت: {maint}",
                     reply_markup=markup)

# ===== کال‌بک‌ها =====
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE banned=1")
        banned = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM messages")
        msgs = cursor.fetchone()[0]

        text = (
            f"📊 <b>آمار کلی</b>\n\n"
            f"👥 کل کاربران: <b>{users}</b>\n"
            f"🚫 بن شده: <b>{banned}</b>\n"
            f"📨 کل پیام‌ها: <b>{msgs}</b>\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 برگشت", callback_data="back_panel"))
        bot.edit_message_text(text, call.message.chat.id,
                              call.message.message_id, reply_markup=markup)

    elif call.data == "daily_stats":
        today = get_today()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE date LIKE ?",
                       (f"{today}%",))
        today_msgs = cursor.fetchone()[0]

        text = (
            f"📈 <b>آمار امروز</b>\n\n"
            f"📅 تاریخ: <b>{today}</b>\n"
            f"📨 پیام‌های امروز: <b>{today_msgs}</b>\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 برگشت", callback_data="back_panel"))
        bot.edit_message_text(text, call.message.chat.id,
                              call.message.message_id, reply_markup=markup)

    elif call.data == "recent_users":
        cursor.execute(
            "SELECT full_name, user_id, last_activity FROM users ORDER BY last_activity DESC LIMIT 10")
        users = cursor.fetchall()

        text = "👥 <b>۱۰ کاربر اخیر:</b>\n\n"
        for i, u in enumerate(users):
            text += f"{i+1}. {u[0]} | <code>{u[1]}</code> | {u[2]}\n"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 برگشت", callback_data="back_panel"))
        bot.edit_message_text(text, call.message.chat.id,
                              call.message.message_id, reply_markup=markup)

    elif call.data == "banlist":
        cursor.execute("SELECT full_name, user_id FROM users WHERE banned=1")
        banned = cursor.fetchall()

        text = "🚫 <b>لیست بن:</b>\n\n"
        if banned:
            for u in banned:
                text += f"👤 {u[0]} | <code>{u[1]}</code>\n"
        else:
            text += "لیست خالی است ✅"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 برگشت", callback_data="back_panel"))
        bot.edit_message_text(text, call.message.chat.id,
                              call.message.message_id, reply_markup=markup)

    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 پیام همگانی را ارسال کن:")
        bot.register_next_step_handler(msg, send_broadcast)

    elif call.data == "change_welcome":
        msg = bot.send_message(call.message.chat.id, "✏️ پیام خوش‌آمدگویی جدید را بفرست:")
        bot.register_next_step_handler(msg, set_welcome)

    elif call.data == "toggle_bot":
        bot_status["active"] = not bot_status["active"]
        status = "🟢 فعال" if bot_status["active"] else "🔴 غیرفعال"
        bot.answer_callback_query(call.id, f"وضعیت: {status}")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_panel(call.message.chat.id)

    elif call.data == "toggle_maintenance":
        bot_status["maintenance"] = not bot_status["maintenance"]
        maint = "🔧 تعمیر" if bot_status["maintenance"] else "✅ عادی"
        bot.answer_callback_query(call.id, f"حالت: {maint}")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_panel(call.message.chat.id)

    elif call.data == "close_panel":
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data == "back_panel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_panel(call.message.chat.id)

    elif call.data.startswith("ban_"):
        user_id = int(call.data.split("_")[1])
        cursor.execute("UPDATE users SET banned=1, ban_until=0 WHERE user_id=?",
                       (user_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "🚫 بن شد")
        bot.edit_message_text(f"🚫 کاربر <code>{user_id}</code> بن شد.",
                              call.message.chat.id, call.message.message_id)

    elif call.data.startswith("unban_"):
        user_id = int(call.data.split("_")[1])
        cursor.execute("UPDATE users SET banned=0, ban_until=0 WHERE user_id=?",
                       (user_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ آزاد شد")
        bot.edit_message_text(f"✅ کاربر <code>{user_id}</code> آزاد شد.",
                              call.message.chat.id, call.message.message_id)

# ===== برودکست =====
def send_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT user_id FROM users WHERE banned=0")
    users = cursor.fetchall()
    success = 0
    fail = 0
    for user in users:
        try:
            bot.send_message(user[0], message.text)
            success += 1
        except:
            fail += 1
    bot.send_message(message.chat.id,
                     f"✅ ارسال شد\n\n📤 موفق: {success}\n❌ ناموفق: {fail}")

# ===== تغییر خوش‌آمدگویی =====
def set_welcome(message):
    if message.from_user.id != ADMIN_ID:
        return
    global welcome_text
    welcome_text = message.text
    bot.send_message(message.chat.id, "✅ پیام خوش‌آمدگویی تغییر کرد!")

# ===== اطلاعات کاربر =====
@bot.message_handler(commands=['info'])
def user_info(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.split()[1])
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        data = cursor.fetchone()

        if not data:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد")
            return

        status = "🚫 بن شده" if data[3] == 1 else "✅ فعال"

        text = (
            f"👤 <b>اطلاعات کاربر</b>\n\n"
            f"📛 نام: <b>{data[2]}</b>\n"
            f"🆔 آیدی: <code>{data[0]}</code>\n"
            f"🔗 یوزرنیم: {show_username(data[1])}\n"
            f"📊 وضعیت: {status}\n"
            f"📨 تعداد پیام‌ها: <b>{data[5]}</b>\n"
            f"🕐 آخرین فعالیت: {data[6]}\n"
            f"📅 تاریخ عضویت: {data[7]}\n"
        )

        markup = types.InlineKeyboardMarkup()
        if data[3] == 0:
            markup.add(types.InlineKeyboardButton("🚫 بن کردن",
                       callback_data=f"ban_{data[0]}"))
        else:
            markup.add(types.InlineKeyboardButton("✅ آزاد کردن",
                       callback_data=f"unban_{data[0]}"))

        bot.send_message(message.chat.id, text, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ استفاده: /info 123456789")

# ===== بن =====
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        duration = int(parts[2]) if len(parts) > 2 else 0

        if duration > 0:
            ban_until = int(time.time()) + (duration * 60)
            cursor.execute("UPDATE users SET banned=1, ban_until=? WHERE user_id=?",
                           (ban_until, user_id))
            conn.commit()
            bot.send_message(message.chat.id,
                             f"🚫 کاربر <code>{user_id}</code> به مدت {duration} دقیقه بن شد")
        else:
            cursor.execute("UPDATE users SET banned=1, ban_until=0 WHERE user_id=?",
                           (user_id,))
            conn.commit()
            bot.send_message(message.chat.id,
                             f"🚫 کاربر <code>{user_id}</code> برای همیشه بن شد")
    except:
        bot.send_message(message.chat.id,
                         "❌ استفاده:\n/ban 123456789\n/ban 123456789 60")

# ===== آنبن =====
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.split()[1])
        cursor.execute("UPDATE users SET banned=0, ban_until=0 WHERE user_id=?",
                       (user_id,))
        conn.commit()
        bot.send_message(message.chat.id,
                         f"✅ کاربر <code>{user_id}</code> آزاد شد")
    except:
        bot.send_message(message.chat.id, "❌ استفاده: /unban 123456789")

# ===== دریافت پیام ناشناس =====
@bot.message_handler(content_types=[
    'text', 'photo', 'video', 'document', 'audio',
    'voice', 'sticker', 'video_note', 'animation'])
def anonymous(message):

    # === پاسخ ادمین ===
    if message.from_user.id == ADMIN_ID:
        if not message.reply_to_message:
            bot.send_message(message.chat.id,
                             "❌ برای پاسخ، روی پیام کاربر ریپلای کن.")
            return

        user_id = get_reply_user_id(message.reply_to_message.message_id)

        if not user_id:
            bot.send_message(message.chat.id,
                             "❌ این پیام قابل شناسایی نیست.")
            return

        try:
            if message.content_type == "text":
                bot.send_message(user_id,
                                 f"📨 <b>پاسخ ادمین:</b>\n\n{message.text}")
            elif message.content_type == "photo":
                bot.send_photo(user_id, message.photo[-1].file_id,
                               caption=f"📨 <b>پاسخ ادمین</b>\n\n{message.caption or ''}")
            elif message.content_type == "video":
                bot.send_video(user_id, message.video.file_id,
                               caption=f"📨 <b>پاسخ ادمین</b>\n\n{message.caption or ''}")
            elif message.content_type == "voice":
                bot.send_voice(user_id, message.voice.file_id)
            elif message.content_type == "audio":
                bot.send_audio(user_id, message.audio.file_id)
            elif message.content_type == "document":
                bot.send_document(user_id, message.document.file_id)
            elif message.content_type == "sticker":
                bot.send_sticker(user_id, message.sticker.file_id)
            elif message.content_type == "video_note":
                bot.send_video_note(user_id, message.video_note.file_id)
            elif message.content_type == "animation":
                bot.send_animation(user_id, message.animation.file_id)

            bot.send_message(message.chat.id, "✅ پاسخ ارسال شد")
        except Exception as e:
            bot.send_message(message.chat.id,
                             f"❌ خطا:\n<code>{e}</code>")
        return

    # === چک وضعیت ربات ===
    if not bot_status["active"]:
        bot.send_message(message.chat.id, "🔴 ربات غیرفعال است.")
        return

    if bot_status["maintenance"]:
        bot.send_message(message.chat.id, "🔧 ربات در حال تعمیر است.")
        return

    register_user(message.from_user)

    # === چک بن ===
    if is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 شما مسدود هستید!")
        return

    # === چک کلمات رکیک ===
    msg_text = message.text or message.caption or ""
    if has_bad_words(msg_text):
        bot.send_message(message.chat.id,
                         "⚠️ پیام شما حاوی کلمات نامناسب است!")
        return

    # === شماره پیام ===
    msg_num = get_msg_number(message.from_user.id)
    now = get_time()

    # === ذخیره پیام ===
    cursor.execute(
        "INSERT INTO messages (user_id, content_type, date) VALUES (?, ?, ?)",
        (message.from_user.id, message.content_type, now))
    cursor.execute(
        "UPDATE users SET last_activity=? WHERE user_id=?",
        (now, message.from_user.id))
    conn.commit()

    # === اطلاعات فرستنده ===
    info = (
        f"📩 <b>پیام ناشناس #{msg_num}</b>\n\n"
        f"👤 نام: <b>{message.from_user.full_name}</b>\n"
        f"🆔 آیدی: <code>{message.from_user.id}</code>\n"
        f"🔗 یوزرنیم: {show_username(message.from_user.username)}\n"
        f"📎 نوع: {message.content_type}\n"
        f"🕐 زمان: {now}\n"
    )

    # === ارسال به ادمین ===
    info_msg = bot.send_message(ADMIN_ID, info)
    fwd_msg = bot.forward_message(ADMIN_ID, message.chat.id,
                                   message.message_id)

    # === ذخیره برای ریپلای ===
    cursor.execute(
        "INSERT OR REPLACE INTO reply_map (admin_message_id, user_id) VALUES (?, ?)",
        (info_msg.message_id, message.from_user.id))
    cursor.execute(
        "INSERT OR REPLACE INTO reply_map (admin_message_id, user_id) VALUES (?, ?)",
        (fwd_msg.message_id, message.from_user.id))
    conn.commit()

    # === تایید برای کاربر ===
    bot.send_message(message.chat.id,
                     "✅ پیام شما با موفقیت ارسال شد!\n\n"
                     "🔒 هویت شما کاملاً محفوظ است.")

print("✅ Bot is running...")
bot.infinity_polling()
