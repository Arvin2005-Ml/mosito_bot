from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import sqlite3
import os
import json
from keep_alive import keep_alive
import asyncio

AGE, INTEREST = range(2)

# اتصال به دیتابیس
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, age INTEGER, interest TEXT)")
conn.commit()

# توکن از محیط
TOKEN = os.environ["TOKEN"]

# مسیر JSON خروجی
JSON_PATH = "users.json"

# تابع آپدیت فایل JSON از دیتابیس
def update_json():
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "age": row[1],
            "interest": row[2]
        })
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# شروع گفتگو
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! سنت چند ساله‌ست؟")
    return AGE

# دریافت سن
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("لطفاً فقط عدد وارد کن 🙂")
        return AGE
    context.user_data["age"] = int(update.message.text)
    await update.message.reply_text("چه حوزه‌ای برات جالبه؟ مثل برنامه‌نویسی، موسیقی، طراحی...")
    return INTEREST

# دریافت علاقه و ذخیره در DB و JSON
async def get_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interest = update.message.text
    user_id = update.effective_user.id
    age = context.user_data["age"]
    c.execute("INSERT OR REPLACE INTO users (id, age, interest) VALUES (?, ?, ?)", (user_id, age, interest))
    conn.commit()
    update_json()  # به‌روزرسانی فایل JSON
    await update.message.reply_text("✅ ممنون! اطلاعاتت ثبت شد.")
    return ConversationHandler.END

# لغو عملیات
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END

# ارسال فایل JSON هنگام دستور /db
async def show_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(JSON_PATH):
        await update.message.reply_document(document=open(JSON_PATH, "rb"), filename="users.json")
    else:
        await update.message.reply_text("هنوز اطلاعاتی ذخیره نشده.")

# تنظیم Webhook و شروع
WEBHOOK_URL = "https://your-app-name.onrender.com/telegram"  # آدرس دامنه رباتت در Render

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interest)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("db", show_db))

    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path="/telegram",
        webhook_url=WEBHOOK_URL
    )
    await app.updater.idle()

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
