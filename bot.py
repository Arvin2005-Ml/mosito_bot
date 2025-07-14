from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    filters, ContextTypes
)
import sqlite3
import os
from keep_alive import keep_alive

# Define states for the conversation
CLASS_SELECTION, AGE_SELECTION = range(2)

# Initialize SQLite database
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, class TEXT, age_range TEXT)")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Welcome message
    await update.message.reply_text("سلام به باشگاه موسینو خوش آمدید! 😊")
    
    # Define class options
    class_options = [
        ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
        ["کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک"],
        ["دوره‌های آموزشی سلول خورشیدی"]
    ]
    reply_keyboard = ReplyKeyboardMarkup(class_options, one_time_keyboard=True)
    
    # Send class selection menu
    await update.message.reply_text(
        "لطفاً یکی از کلاس‌های آموزشی زیر را انتخاب کنید:",
        reply_markup=reply_keyboard
    )
    return CLASS_SELECTION

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_class = update.message.text
    valid_classes = [
        "کلاس آموزشی رباتیک", "کلاس آموزشی پایتون",
        "کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک",
        "دوره‌های آموزشی سلول خورشیدی"
    ]
    
    if selected_class not in valid_classes:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید. 😊")
        return CLASS_SELECTION
    
    context.user_data["class"] = selected_class
    
    # Define age ranges
    age_options = [
        ["8-10 سال", "10-14 سال"],
        ["14-15 سال", "20-35 سال"]
    ]
    reply_keyboard = ReplyKeyboardMarkup(age_options, one_time_keyboard=True)
    
    # Ask for age
    await update.message.reply_text(
        "شما چند سال سن دارید؟ لطفاً بازه سنی خود را انتخاب کنید:",
        reply_markup=reply_keyboard
    )
    return AGE_SELECTION

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_range = update.message.text
    valid_ages = ["8-10 سال", "10-14 سال", "14-15 سال", "20-35 سال"]
    
    if age_range not in valid_ages:
        await update.message.reply_text("لطفاً یکی از بازه‌های سنی منو را انتخاب کنید. 😊")
        return AGE_SELECTION
    
    selected_class = context.user_data["class"]
    
    # Check if AI class is selected and age is 8-10
    if selected_class == "کلاس آموزشی هوش مصنوعی" and age_range == "8-10 سال":
        await update.message.reply_text(
            "متأسفیم، کلاس هوش مصنوعی برای بازه سنی 8-10 سال مناسب نیست. لطفاً کلاس دیگری انتخاب کنید.",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
                    ["کلاس زبان انگلیسی تخصصی رباتیک", "دوره‌های آموزشی سلول خورشیدی"]
                ],
                one_time_keyboard=True
            )
        )
        return CLASS_SELECTION
    
    # Store user data in database
    user_id = update.effective_user.id
    c.execute("INSERT OR REPLACE INTO users (id, class, age_range) VALUES (?, ?, ?)", 
             (user_id, selected_class, age_range))
    conn.commit()
    
    # Send Instagram link and ID
    await update.message.reply_text(
        "✅ ممنون از ثبت اطلاعات! 😊\n"
        "برای اطلاعات بیشتر، ما را در اینستاگرام دنبال کنید:\n"
        "لینک: https://www.instagram.com/musino_academy\n"
        "آیدی: @MusinoAcademy",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ["TOKEN"]
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
            AGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.run_polling()
