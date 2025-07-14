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

# Initialize SQLite database with error handling
try:
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, class TEXT, age_range TEXT)")
    conn.commit()
except sqlite3.Error as e:
    print(f"Database error: {e}")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /start command and show class selection menu."""
    try:
        await update.message.reply_text("سلام به باشگاه موسینو خوش آمدید! 😊")
        
        # Define class options
        class_options = [
            ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
            ["کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک"],
            ["دوره‌های آموزشی سلول خورشیدی"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "لطفاً یکی از کلاس‌های آموزشی زیر را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return CLASS_SELECTION
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in start: {e}")
        return ConversationHandler.END

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle class selection and validate input."""
    try:
        selected_class = update.message.text
        valid_classes = [
            "کلاس آموزشی رباتیک", "کلاس آموزشی پایتون",
            "کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک",
            "دوره‌های آموزشی سلول خورشیدی"
        ]
        
        if selected_class not in valid_classes:
            await update.message.reply_text("لطفاً فقط یکی از گزینه‌های منو را انتخاب کنید. 😊")
            return CLASS_SELECTION
        
        context.user_data["class"] = selected_class
        
        # Define age ranges
        age_options = [
            ["8-10 سال", "10-14 سال"],
            ["14-15 سال", "20-35 سال"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(age_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "شما چند سال سن دارید؟ لطفاً بازه سنی خود را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return AGE_SELECTION
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in get_class: {e}")
        return ConversationHandler.END

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle age selection, validate, and store data."""
    try:
        age_range = update.message.text
        valid_ages = ["8-10 سال", "10-14 سال", "14-15 سال", "20-35 سال"]
        
        if age_range not in valid_ages:
            await update.message.reply_text("لطفاً فقط یکی از بازه‌های سنی منو را انتخاب کنید. 😊")
            return AGE_SELECTION
        
        selected_class = context.user_data.get("class")
        
        # Check if AI class is selected and age is 8-10
        if selected_class == "کلاس آموزشی هوش مصنوعی" and age_range == "8-10 سال":
            class_options = [
                ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
                ["کلاس زبان انگلیسی تخصصی رباتیک", "دوره‌های آموزشی سلول خورشیدی"]
            ]
            await update.message.reply_text(
                "متأسفیم، کلاس هوش مصنوعی برای بازه سنی 8-10 سال مناسب نیست. لطفاً کلاس دیگری انتخاب کنید.",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        
        # Store user data in database
        user_id = update.effective_user.id
        try:
            c.execute("INSERT OR REPLACE INTO users (id, class, age_range) VALUES (?, ?, ?)", 
                     (user_id, selected_class, age_range))
            conn聆conn.commit()
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"Database error in get_age: {e}")
            return ConversationHandler.END
        
        # Send Instagram link and thank-you message
        await update.message.reply_text(
            "✅ ممنون از ثبت اطلاعات! 😊\n"
            "برای اطلاعات بیشتر، ما را در اینستاگرام دنبال کنید:\n"
            "لینک: https://www.instagram.com/musino_academy\n"
            "آیدی: @MusinoAcademy",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in get_age: {e}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /cancel command."""
    try:
        await update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in cancel: {e}")
        return ConversationHandler.END

if __name__ == "__main__":
    try:
        keep_alive()
        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("Error: TOKEN environment variable not set")
            exit(1)
        
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
    except Exception as e:
        print(f"Error in main: {e}")
        exit(1)

# Ensure database connection is closed when program exits
def cleanup():
    conn.close()

import atexit
atexit.register(cleanup)
