from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    filters, ContextTypes
)
import sqlite3
import os
import asyncio
from keep_alive import keep_alive

# Define states for the conversation
CLASS_SELECTION, AGE_SELECTION, NAME_INPUT, PHONE_INPUT = range(4)

# Initialize SQLite database
try:
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, class TEXT, age_range TEXT, name TEXT, phone TEXT)")
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
    """Handle age selection and validate."""
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
        
        context.user_data["age_range"] = age_range
        
        # Ask for name
        await update.message.reply_text(
            "لطفاً نام خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME_INPUT
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in get_age: {e}")
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    try:
        name = update.message.text.strip()
        if not name:
            await update.message.reply_text("لطفاً نام معتبر وارد کنید. 😊")
            return NAME_INPUT
        
        context.user_data["name"] = name
        
        # Request phone number with Share Contact button
        reply_keyboard = [[KeyboardButton("اشتراک شماره تماس", request_contact=True)]]
        await update.message.reply_text(
            "لطفاً شماره تماس خود را با استفاده از دکمه زیر به اشتراک بگذارید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PHONE_INPUT
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"Error in get_name: {e}")
        return ConversationHandler.END

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input via contact or text."""
    try:
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
        else:
            phone = update.message.text.strip()
            # Basic phone number validation (accepts digits and optional +)
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()):
                await update.message.reply_text("لطفاً شماره تماس معتبر وارد کنید یا از دکمه اشتراک استفاده کنید. 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        
        # Store data in database
        try:
            c.execute("INSERT OR REPLACE INTO users (id, class, age_range, name, phone) VALUES (?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone))
            conn.commit()
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"Database error in get_phone: {e}")
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
        print(f"Error in get_phone: {e}")
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
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.CONTACT, get_phone)],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        app.add_handler(conv)
        
        # Run polling with graceful stop
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(app.run_polling(allowed_updates=Update.ALL_TYPES))
        finally:
            loop.run_until_complete(app.updater.stop())
            loop.run_until_complete(app.stop())
            loop.close()
    except Exception as e:
        print(f"Error in main: {e}")
        exit(1)

# Ensure database connection is closed on exit
def cleanup():
    try:
        conn.close()
        print("Database connection closed")
    except Exception as e:
        print(f"Error closing database: {e}")

import atexit
atexit.register(cleanup)
