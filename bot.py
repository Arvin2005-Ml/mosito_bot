from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import sqlite3
import os
from keep_alive import keep_alive

# وضعیت‌های گفتگو
AGE, INTEREST = range(2)

# اتصال به دیتابیس
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, age INTEGER, interest TEXT)")
conn.commit()

# شروع گفتگو
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! سنت چقدره؟")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data["age"] = age
        await update.message.reply_text("چه حوزه‌ای برات جذابه؟ (مثلاً برنامه‌نویسی، طراحی، موسیقی...)")
        return INTEREST
    except:
        await update.message.reply_text("عدد وارد کن لطفاً. سنت چقدره؟")
        return AGE

async def get_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interest = update.message.text
    user_id = update.effective_user.id
    age = context.user_data["age"]
    c.execute("INSERT OR REPLACE INTO users (id, age, interest) VALUES (?, ?, ?)", (user_id, age, interest))
    conn.commit()
    await update.message.reply_text("مرسی! اطلاعاتت ذخیره شد ✅")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get("TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interest)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()