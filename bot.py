from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    filters, ContextTypes
)
import sqlite3
import os
from keep_alive import keep_alive

AGE, INTEREST = range(2)

conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, age INTEGER, interest TEXT)")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! سنت چند ساله‌ست؟")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("لطفاً فقط عدد وارد کن 🙂")
        return AGE
    context.user_data["age"] = int(update.message.text)
    await update.message.reply_text("چه حوزه‌ای برات جالبه؟ مثل برنامه‌نویسی، موسیقی، طراحی...")
    return INTEREST

async def get_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interest = update.message.text
    user_id = update.effective_user.id
    age = context.user_data["age"]
    c.execute("INSERT OR REPLACE INTO users (id, age, interest) VALUES (?, ?, ?)", (user_id, age, interest))
    conn.commit()
    await update.message.reply_text("✅ ممنون! اطلاعاتت ثبت شد.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ["TOKEN"]
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
    app.run_polling()
